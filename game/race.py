"""The race itself: car physics, rival AI, weather and the heads-up display."""

import math
import random

import pygame

from . import cars as garage
from . import pixelfont as pf
from .config import BASE_HEIGHT, BASE_WIDTH, SCALE
from .render import (WIDTH, HEIGHT, DRAW_DISTANCE, OBJECT_SCALE, CAMERA_HEIGHT,
                     CAMERA_DEPTH, sprite_anchor)
from .track import SEGMENT_LENGTH, ROAD_WIDTH

STEP = 1.0 / 60.0
MAX_SPEED = SEGMENT_LENGTH / STEP          # 12000 units per second
ACCEL = MAX_SPEED / 4.6
BRAKING = -MAX_SPEED / 1.5
DECEL = -MAX_SPEED / 7.0
OFF_ROAD_DECEL = -MAX_SPEED / 1.6
OFF_ROAD_LIMIT = MAX_SPEED / 3.6
CENTRIFUGAL = 0.46
KMH_PER_UNIT = 310.0 / MAX_SPEED
GEARS = 5
PLAYER_W = 0.32       # car width in road half-widths
RIVAL_W = 0.32        # rivals are the same width, and must look it
INK = (236, 240, 250)
# HUD geometry on the 320x200 design grid. The player car is placed against
# HUD_BOTTOM so the instrument panel cannot swallow its wheels.
HUD_TOP = 24
HUD_BOTTOM = 16
CAR_SINK = 4          # how far the car's bottom tucks behind the panel
TURBO_TIME = 2.6
TURBO_BOOST = 1.22


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def overlap(x1, w1, x2, w2, slack=0.85):
    return abs(x1 - x2) < (w1 + w2) / 2 * slack


class Rival:
    __slots__ = ('z', 'offset', 'speed', 'sprite', 'size', 'colour', 'lean',
                 'seg', 'total', 'lap')

    def __init__(self, z, offset, speed, colour):
        self.z = z
        self.offset = offset
        self.speed = speed
        self.colour = colour
        self.lean = 1
        self.size = 0.97      # overwritten from the real sprite on spawn
        self.sprite = 'car_rival%d_1' % colour
        self.seg = None
        self.total = z
        self.lap = 0


class Player:
    def __init__(self):
        self.z = 0.0
        self.x = 0.0
        self.speed = 0.0
        self.steer = 0.0          # -1..1 smoothed input
        self.slide = 0.0
        self.bounce = 0.0
        self.turbo = 3
        self.turbo_left = 0.0
        self.braking = False
        self.offroad = False
        self.lap = 0
        self.total = 0.0


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'kind', 'size')

    def __init__(self, x, y, vx, vy, life, kind, size=0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = life
        self.kind = kind
        self.size = size


class Race:
    """Owns one attempt at one circuit."""

    STATE_COUNTDOWN = 0
    STATE_RACING = 1
    STATE_FINISHED = 2
    STATE_TIMEUP = 3

    def __init__(self, track, renderer, audio, scores, rng=None, car=None):
        self.car = car or garage.DEFAULT
        self.top_speed = MAX_SPEED * self.car['speed']
        self.car_accel = ACCEL * self.car['accel']
        self.car_body = self.car['body']
        self.track = track
        self.r = renderer
        self.audio = audio
        self.scores = scores
        self.rng = rng or random.Random()
        self.colors = renderer.colors_for(track.theme)
        self.player = Player()
        self.cars = []
        self.state = self.STATE_COUNTDOWN
        self.countdown = 3.9
        self.time_left = float(track.start_time)
        self.race_time = 0.0
        self.lap_time = 0.0
        self.lap_times = []
        self.best_lap = None
        self.position = 1
        self.messages = []          # (text, ttl, colour, big)
        self.particles = []
        self.weather = []
        self.sky_off = 0.0
        self.hill_off = 0.0
        self.tree_off = 0.0
        self.shake = 0.0
        self.finished_at = None
        self.acc = 0.0
        self.flash = 0.0
        self._puff_cache = {}
        self.revs = 0.16
        self._spawn_rivals()
        self._init_weather()

    # -- setup ----------------------------------------------------------
    def _spawn_rivals(self):
        n = self.track.rivals
        total = len(self.track.segments)
        # Derive the draw scale from the collision width and the actual sprite,
        # so a rival can never render narrower than the box you hit.
        sprite_w = self.r.assets.get('car_rival0_1').get_width()
        size = RIVAL_W * ROAD_WIDTH / (sprite_w * OBJECT_SCALE)
        for i in range(n):
            z = (i + 1) * (self.track.length / (n + 1.0)) * 0.55 + 1500
            off = self.rng.choice([-0.62, -0.24, 0.24, 0.62]) \
                + self.rng.uniform(-0.06, 0.06)
            speed = MAX_SPEED * self.rng.uniform(0.56, 0.80) \
                * self.track.par_speed
            car = Rival(z % self.track.length, off, speed, i % 6)
            car.size = size
            seg = self.track.segment_at(car.z)
            seg.cars.append(car)
            car.seg = seg
            self.cars.append(car)
        self._total_segments = total

    def _init_weather(self):
        kind = self.track.theme['weather']
        if not kind:
            return
        n = 90 if kind == 'snow' else 60
        for _ in range(n):
            self.weather.append(Particle(
                self.rng.uniform(0, WIDTH), self.rng.uniform(0, HEIGHT),
                self.rng.uniform(-8, 8), self.rng.uniform(20, 70), 0, kind,
                self.rng.randint(1, 2)))

    def clear(self):
        """Detach rivals from the shared track segment lists."""
        for car in self.cars:
            if car.seg is not None and car in car.seg.cars:
                car.seg.cars.remove(car)
            car.seg = None

    # -- helpers --------------------------------------------------------
    def message(self, text, ttl=1.6, colour=(255, 236, 120), big=True):
        self.messages.append([text, ttl, colour, big])

    @property
    def speed_ratio(self):
        return self.player.speed / MAX_SPEED

    @property
    def kmh(self):
        return self.player.speed * KMH_PER_UNIT

    def gear_rpm(self):
        if self.state == self.STATE_COUNTDOWN:
            return 1, clamp(self.revs, 0.0, 1.0)
        r = clamp(self.player.speed / self.top_speed, 0.0, 1.0)
        g = min(GEARS - 1, int(r * GEARS))
        frac = r * GEARS - g
        return g + 1, 0.22 + 0.78 * frac

    # -- simulation -----------------------------------------------------
    def update(self, dt, keys):
        dt = min(dt, 0.1)
        self.acc += dt
        while self.acc >= STEP:
            self._step(STEP, keys)
            self.acc -= STEP
        self._update_effects(dt)

    def _step(self, dt, keys):
        p = self.player
        track = self.track
        grip = track.theme['grip']

        if self.state == self.STATE_COUNTDOWN:
            prev = int(self.countdown)
            self.countdown -= dt
            now = int(self.countdown)
            if now != prev and 0 <= now <= 3:
                if now == 0:
                    self.audio.play('sfx_go')
                    self.message('GO!', 1.1, (140, 255, 140))
                else:
                    self.audio.play('sfx_countdown')
            if self.countdown <= 0:
                self.state = self.STATE_RACING
            # The car is held on the line. Blipping the throttle revs the
            # engine, but it cannot build road speed before the lights go
            # out - every race starts from a standstill.
            p.speed = 0.0
            target = 0.92 if keys['accel'] else 0.16
            self.revs += (target - self.revs) * min(1.0, dt * 7.0)
            self.audio.engine(self.revs, 0.25 + 0.45 * self.revs)
            self._advance_rivals(dt, idle=True)
            return

        if self.state in (self.STATE_FINISHED, self.STATE_TIMEUP):
            p.speed = max(0.0, p.speed + DECEL * dt * 2.4)
            p.z = (p.z + p.speed * dt) % track.length
            self._advance_rivals(dt)
            return

        # ---- timers
        self.time_left -= dt
        self.race_time += dt
        self.lap_time += dt
        if self.time_left <= 0:
            self.time_left = 0.0
            self.state = self.STATE_TIMEUP
            self.audio.play('sfx_gameover')
            self.message('OUT OF TIME', 3.0, (255, 110, 110))
            return

        seg = track.segment_at(p.z)
        speed_pct = p.speed / MAX_SPEED

        # ---- steering
        target = (-1.0 if keys['left'] else 0.0) + (1.0 if keys['right'] else 0.0)
        p.steer += (target - p.steer) * min(1.0, dt * 11.0)
        steer_rate = 2.5 * speed_pct * (0.55 + 0.45 * grip) \
            * self.car['grip']
        p.x += p.steer * steer_rate * dt

        # ---- centrifugal push. It grows with the square of speed while
        # steering authority only grows linearly, so fast corners have to be
        # taken slower - lifting off is what makes a lap quick.
        drift = dt * speed_pct * speed_pct * seg.curve * CENTRIFUGAL \
            / max(0.5, grip)
        p.x -= drift
        p.slide += (abs(drift) * 42.0 - p.slide) * min(1.0, dt * 5.0)

        # ---- throttle
        boosting = p.turbo_left > 0
        if boosting:
            p.turbo_left -= dt
        top = self.top_speed * (TURBO_BOOST if boosting else 1.0)
        p.braking = keys['brake'] and p.speed > 0
        if keys['accel']:
            p.speed += self.car_accel * dt * (1.35 if boosting else 1.0)
        elif keys['brake']:
            p.speed += BRAKING * dt
        else:
            p.speed += DECEL * dt

        p.offroad = abs(p.x) > 1.0
        if p.offroad:
            if p.speed > OFF_ROAD_LIMIT:
                p.speed += OFF_ROAD_DECEL * dt
            self._collide_scenery(seg)
            if self.rng.random() < 0.5:
                self._dust(1 if p.x > 0 else -1)
        p.speed = clamp(p.speed, 0.0, top)
        if not keys['accel'] and not boosting:
            p.speed = min(p.speed, self.top_speed)

        self._collide_cars(seg)
        p.x = clamp(p.x, -2.4, 2.4)

        # ---- advance
        old_z = p.z
        p.z += p.speed * dt
        if p.z >= track.length:
            p.z -= track.length
            self._complete_lap()
        p.total += p.speed * dt

        self._advance_rivals(dt)
        self._update_position()

        # ---- camera / parallax
        self.sky_off += seg.curve * speed_pct * dt * 4.0
        self.hill_off += seg.curve * speed_pct * dt * 12.0
        self.tree_off += seg.curve * speed_pct * dt * 26.0
        p.bounce = (p.bounce + dt * (4.0 + speed_pct * 26.0)) % (math.pi * 2)

        # ---- audio
        gear, rpm = self.gear_rpm()
        self.audio.engine(rpm, 0.35 + 0.65 * speed_pct if keys['accel']
                          else 0.18 + 0.4 * speed_pct)
        skid = (abs(p.steer) > 0.55 and speed_pct > 0.55 and
                abs(seg.curve) > 1.5) or p.offroad or \
               (p.braking and speed_pct > 0.6)
        self.audio.skid(skid, clamp(speed_pct, 0.2, 0.8))

    def _complete_lap(self):
        p = self.player
        p.lap += 1
        lap_t = self.lap_time
        self.lap_times.append(lap_t)
        self.lap_time = 0.0
        if self.best_lap is None or lap_t < self.best_lap:
            self.best_lap = lap_t
        if p.lap >= self.track.laps:
            self.state = self.STATE_FINISHED
            self.finished_at = self.race_time
            self.audio.play('sfx_fanfare')
            self.message('FINISH!', 3.0, (140, 255, 160))
        else:
            self.time_left += self.track.lap_bonus
            self.flash = 0.5
            self.audio.play('sfx_lap')
            self.audio.play('sfx_extend', 0.7)
            self.message('LAP %d  +%dS' % (p.lap + 1, self.track.lap_bonus),
                         1.8, (255, 236, 120))

    def _advance_rivals(self, dt, idle=False):
        track = self.track
        p = self.player
        n = len(track.segments)
        p_seg_i = int(p.z / SEGMENT_LENGTH) % n
        for car in self.cars:
            if not idle:
                car.offset += self._rival_steer(car, p_seg_i) * dt
                car.offset = clamp(car.offset, -0.92, 0.92)
            old = car.seg
            car.z += car.speed * dt * (0.0 if idle else 1.0)
            car.total += car.speed * dt * (0.0 if idle else 1.0)
            if car.z >= track.length:
                car.z -= track.length
                car.lap += 1
            new = track.segment_at(car.z)
            if new is not old:
                if old is not None and car in old.cars:
                    old.cars.remove(car)
                new.cars.append(car)
                car.seg = new
            lean = 1
            if new.curve > 2:
                lean = 2
            elif new.curve < -2:
                lean = 0
            car.sprite = 'car_rival%d_%d' % (car.colour, lean)

    def _rival_steer(self, car, player_seg_i):
        """Look a short way ahead and drift out of the way of anything close."""
        track = self.track
        n = len(track.segments)
        base = int(car.z / SEGMENT_LENGTH) % n
        look = 18
        if self.car['yield_traffic']:
            # sirens: rivals pull over well before the player arrives
            gap = (base - player_seg_i) % n
            if gap < 42 and overlap(self.player.x, self.car_body + 0.5,
                                    car.offset, RIVAL_W, 1.0):
                return -1.4 if self.player.x > car.offset else 1.4
        for i in range(1, look):
            seg = track.segments[(base + i) % n]
            if (base + i) % n == player_seg_i and \
                    car.speed > self.player.speed and \
                    overlap(self.player.x, self.car_body, car.offset, RIVAL_W,
                            1.4):
                return -0.9 if self.player.x > car.offset else 0.9
            for other in seg.cars:
                if other is car:
                    continue
                if car.speed > other.speed and \
                        overlap(car.offset, RIVAL_W, other.offset, RIVAL_W,
                                1.3):
                    return -0.7 if other.offset > car.offset else 0.7
        # ease back toward the middle of the road
        if car.offset < -0.75:
            return 0.35
        if car.offset > 0.75:
            return -0.35
        return 0.0

    def _collide_scenery(self, seg):
        p = self.player
        for offset, name, sc, collides in seg.sprites:
            if not collides:
                continue
            img = self.r.assets.get(name)
            w = img.get_width() * sc * OBJECT_SCALE / ROAD_WIDTH
            cx = sprite_anchor(offset, w)
            if overlap(p.x, self.car_body, cx, w, 0.7):
                self._crash(offset)
                return

    def _collide_cars(self, seg):
        p = self.player
        for car in list(seg.cars):
            if p.speed <= car.speed:
                continue
            if overlap(p.x, self.car_body, car.offset, RIVAL_W, 0.85):
                keep = 0.72 + 0.14 * (self.car['mass'] - 1.0)
                p.speed = max(car.speed * clamp(keep, 0.6, 0.95),
                              p.speed * 0.55)
                p.x += 0.16 if p.x > car.offset else -0.16
                p.z = max(0.0, p.z - SEGMENT_LENGTH * 1.2)
                self.shake = max(self.shake, 3.2)
                self.audio.play('sfx_crash', 0.6)
                for _ in range(9):
                    self._smoke()
                return

    def _crash(self, offset):
        p = self.player
        p.speed = min(p.speed, OFF_ROAD_LIMIT * (0.55 + 0.22 *
                                                 (self.car['mass'] - 1.0)))
        p.x = clamp(p.x, -1.02, 1.02) * 0.92
        self.shake = max(self.shake, 5.5)
        self.audio.play('sfx_crash')
        for _ in range(14):
            self._smoke()

    def _smoke(self):
        self.particles.append(Particle(
            WIDTH / 2 + self.rng.uniform(-34, 34) * SCALE,
            HEIGHT - 26 * SCALE,
            self.rng.uniform(-40, 40) * SCALE,
            self.rng.uniform(-46, -8) * SCALE,
            self.rng.uniform(0.35, 0.85), 'smoke', self.rng.randint(0, 2)))

    def _dust(self, side):
        self.particles.append(Particle(
            WIDTH / 2 + side * self.rng.uniform(22, 44) * SCALE,
            HEIGHT - 20 * SCALE,
            side * self.rng.uniform(6, 40) * SCALE,
            self.rng.uniform(-30, -4) * SCALE,
            self.rng.uniform(0.25, 0.55), 'smoke', self.rng.randint(0, 2)))

    def _update_position(self):
        p = self.player
        mine = p.lap * self.track.length + p.z
        ahead = 0
        for car in self.cars:
            if car.lap * self.track.length + car.z > mine:
                ahead += 1
        self.position = ahead + 1

    def _update_effects(self, dt):
        self.shake = max(0.0, self.shake - dt * 12.0)
        self.flash = max(0.0, self.flash - dt * 2.0)
        for m in self.messages:
            m[1] -= dt
        self.messages = [m for m in self.messages if m[1] > 0]
        alive = []
        for pt in self.particles:
            pt.life -= dt
            if pt.life <= 0:
                continue
            pt.x += pt.vx * dt
            pt.y += pt.vy * dt
            pt.vy += 40 * dt * SCALE
            alive.append(pt)
        self.particles = alive
        if self.weather:
            sp = 1.0 + self.speed_ratio * 3.0
            for pt in self.weather:
                pt.y += pt.vy * dt * sp
                pt.x += pt.vx * dt + math.sin(pt.y * 0.05) * 12 * dt
                if pt.y > HEIGHT:
                    pt.y = -4
                    pt.x = self.rng.uniform(0, WIDTH)
                if pt.x < -4:
                    pt.x = WIDTH
                elif pt.x > WIDTH + 4:
                    pt.x = 0

    def use_turbo(self):
        p = self.player
        if self.state == self.STATE_RACING and p.turbo > 0 and p.turbo_left <= 0:
            p.turbo -= 1
            p.turbo_left = TURBO_TIME
            self.audio.play('sfx_select', 0.7)
            self.message('TURBO!', 1.0, (255, 170, 60))

    # -- drawing --------------------------------------------------------
    def draw(self, surface, ui=None):
        """World goes to `surface`; the HUD goes to `ui`, which in hi-res mode
        is a separate 320x200 layer scaled up later so the font stays crisp."""
        r = self.r
        r.surface = surface
        th = self.track.theme
        p = self.player
        horizon = HEIGHT * 0.5 + 4 * SCALE
        shake_y = int(math.sin(self.shake * 9) * self.shake) * SCALE
        r.draw_background(th, self.sky_off, self.hill_off, self.tree_off,
                          horizon + shake_y)
        base_i, _ = r.draw_road(self.track, p.z, p.x,
                                CAMERA_HEIGHT + shake_y * 30, self.colors)
        r.draw_scene_sprites(self.track, base_i, self.colors, p, self.cars,
                             self._player_sprite(shake_y))
        self._draw_particles(surface)
        if th['ambient']:
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            tint.fill(th['ambient'])
            surface.blit(tint, (0, 0))
        self._draw_weather(surface)
        self._draw_speedlines(surface)
        self.draw_hud(ui if ui is not None else surface)

    def _player_sprite(self, shake_y):
        p = self.player
        lean = 0
        if p.steer < -0.55:
            lean = 0
        elif p.steer < -0.18:
            lean = 1
        elif p.steer > 0.55:
            lean = 4
        elif p.steer > 0.18:
            lean = 3
        else:
            lean = 2
        name = 'car_%s_%d%s' % (self.car['key'], lean,
                                'b' if p.braking else 'n')
        img = self.r.assets.get(name)
        w = self.car['width'] * SCALE
        h = int(img.get_height() * w / img.get_width())
        surf = self.r.assets.scaled(name, w, h)
        bob = (math.sin(p.bounce) * (1.0 + self.speed_ratio * 1.6)) * SCALE
        if p.offroad:
            bob += math.sin(p.bounce * 3.1) * 2.2 * SCALE
        x = WIDTH / 2 - w / 2 + p.steer * 3 * SCALE
        y = HEIGHT - (HUD_BOTTOM - CAR_SINK) * SCALE - h + bob \
            + shake_y
        return surf, (int(x), int(y))

    def _draw_particles(self, s):
        cache = self._puff_cache
        for pt in self.particles:
            step = int(clamp(pt.life * 1.6, 0, 1) * 6)
            key = (pt.size, step)
            img = cache.get(key)
            if img is None:
                src = self.r.assets.get('fx_smoke%d' % pt.size)
                if SCALE > 1:
                    src = pygame.transform.scale(
                        src, (src.get_width() * SCALE,
                              src.get_height() * SCALE))
                img = src.copy()
                img.set_alpha(int(220 * step / 6.0))
                cache[key] = img
            s.blit(img, (int(pt.x), int(pt.y)))

    def _draw_weather(self, s):
        if not self.weather:
            return
        kind = self.track.theme['weather']
        col = (246, 250, 255) if kind == 'snow' else (226, 196, 140)
        for pt in self.weather:
            s.fill(col, (int(pt.x), int(pt.y), pt.size * SCALE,
                        (pt.size + 1) * SCALE))

    def _draw_speedlines(self, s):
        r = self.speed_ratio
        if r < 0.72:
            return
        n = int((r - 0.72) * 60)
        cx, cy = WIDTH / 2, HEIGHT * 0.55
        for i in range(n):
            a = self.rng.uniform(0, math.pi * 2)
            d0 = self.rng.uniform(60, 120) * SCALE
            ln = (8 + (r - 0.72) * 40) * SCALE
            x0 = cx + math.cos(a) * d0
            y0 = cy + math.sin(a) * d0 * 0.6
            x1 = cx + math.cos(a) * (d0 + ln)
            y1 = cy + math.sin(a) * (d0 + ln) * 0.6
            pygame.draw.line(s, (255, 255, 255), (x0, y0), (x1, y1))

    # -- HUD ------------------------------------------------------------
    def draw_hud(self, s):
        """Two thin strips: everything you glance at lives on the top bar, and
        the bottom keeps a single line for the numbers you watch continuously."""
        p = self.player
        W, H = BASE_WIDTH, BASE_HEIGHT

        panel = pygame.Surface((W, HUD_TOP), pygame.SRCALPHA)
        panel.fill((10, 10, 22, 172))
        s.blit(panel, (0, 0))
        s.fill((198, 40, 60), (0, HUD_TOP, W, 1))

        pf.draw_text(s, 'LAP', 4, 3, (150, 156, 180), 1)
        pf.draw_text(s, '%d/%d' % (min(p.lap + 1, self.track.laps),
                                   self.track.laps), 4, 13, INK, 1)
        pf.draw_text(s, 'POS', 36, 3, (150, 156, 180), 1)
        pf.draw_text(s, '%d/%d' % (self.position, self.track.rivals + 1),
                     36, 13, INK, 1)

        # the countdown, the one number that decides the race
        t = self.time_left
        col = INK
        if t < 6:
            col = (255, 90, 90) if int(t * 4) % 2 == 0 else (255, 200, 60)
        elif self.flash > 0 and int(self.flash * 12) % 2 == 0:
            col = (140, 255, 150)
        pf.draw_text(s, '%02d' % int(min(99, math.ceil(t))), W // 2, 2,
                     col, 3, center=True, shadow=(60, 10, 20))

        pf.draw_text(s, 'TIME', 256, 3, (150, 156, 180), 1, right=True)
        pf.draw_text(s, fmt(self.lap_time), 256, 13, (255, 236, 120), 1,
                     right=True)
        s.fill((70, 74, 96), (262, 4, 1, HUD_TOP - 8))
        pf.draw_text(s, 'BEST', W - 4, 3, (150, 156, 180), 1, right=True)
        pf.draw_text(s, fmt(self.best_lap), W - 4, 13, (170, 210, 255), 1,
                     right=True)

        # single-line instrument strip
        top = H - HUD_BOTTOM
        base = pygame.Surface((W, HUD_BOTTOM), pygame.SRCALPHA)
        base.fill((10, 10, 22, 172))
        s.blit(base, (0, top))
        s.fill((198, 40, 60), (0, top - 1, W, 1))

        pf.draw_text(s, '%3d' % int(self.kmh), 4, top + 1, (255, 240, 140), 2,
                     shadow=(60, 10, 20))
        pf.draw_text(s, 'KM/H', 42, top + 5, (170, 176, 200), 1)
        gear, rpm = self.gear_rpm()
        pf.draw_text(s, 'GEAR %d' % gear, 70, top + 5, (200, 206, 226), 1)

        bx, by, bw = 110, top + 5, 44
        s.fill((40, 40, 56), (bx, by, bw, 6))
        n = int(rpm * bw)
        for i in range(n):
            c = (90, 220, 110) if i < bw * 0.62 else (
                (255, 210, 70) if i < bw * 0.84 else (255, 70, 70))
            s.fill(c, (bx + i, by, 1, 6))
        if p.turbo_left > 0:
            pf.draw_text(s, 'BOOST', 160, top + 5, (255, 170, 60), 1)

        for i in range(3):
            x = W - 11 - i * 9
            on = i < p.turbo
            c = (255, 150, 40) if on else (58, 58, 74)
            if p.turbo_left > 0 and i == p.turbo and int(
                    p.turbo_left * 10) % 2 == 0:
                c = (255, 240, 160)
            s.fill(c, (x, top + 4, 7, 8))
        pf.draw_text(s, 'TURBO', W - 32, top + 5, (170, 176, 200), 1,
                     right=True)

        # centre messages
        y = 76
        for text, ttl, colour, big in self.messages:
            if ttl > 0:
                pf.draw_text(s, text, W // 2, y, colour, 2 if big else 1,
                             center=True, shadow=(20, 12, 30))
                y += 20

        if self.state == self.STATE_COUNTDOWN and self.countdown > 0:
            n = int(math.ceil(self.countdown - 0.9))
            if n >= 1:
                pf.draw_text(s, str(min(3, n)), W // 2, 56, (255, 236, 120),
                             6, center=True, shadow=(120, 20, 40))

        if p.offroad and self.state == self.STATE_RACING:
            if int(self.race_time * 6) % 2 == 0:
                pf.draw_text(s, 'OFF ROAD', W // 2, H - 34, (255, 120, 120),
                             1, center=True)


def fmt(t):
    if t is None:
        return '--:--.--'
    m = int(t // 60)
    return '%d:%05.2f' % (m, t - m * 60)
