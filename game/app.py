"""Front end: title screen with an attract-mode demo running behind it,
circuit select, pause, results and the 3-character high score entry."""

import math
import os
import random

import pygame

from . import pixelfont as pf
from . import autopilot
from . import cars as garage
from . import difficulty as levels
from . import track as tracks
from .audio import Audio
from .race import Race, fmt, MAX_SPEED
from .config import BASE_HEIGHT, BASE_WIDTH, HIRES, SCALE
from .render import Assets, Renderer, WIDTH, HEIGHT
from .scores import Scores, ALPHABET, NAME_LEN, TABLE_SIZE

TITLE = 'LATE APEX'
BASE_SCALE = 3

(S_TITLE, S_SELECT, S_DIFF, S_CAR, S_RACE, S_PAUSE, S_RESULT, S_NAME,
 S_SCORES, S_HELP) = range(10)

ACCENT = (255, 210, 60)
ACCENT2 = (255, 90, 90)
INK = (236, 240, 250)
DIM = (150, 158, 186)


class App:
    def __init__(self, root):
        pygame.init()
        self.root = root
        self.audio = Audio(root)
        self.scale = max(1, BASE_SCALE // SCALE)
        self.fullscreen = False
        self.window = pygame.display.set_mode(
            (BASE_WIDTH * BASE_SCALE, BASE_HEIGHT * BASE_SCALE))
        pygame.display.set_caption(TITLE)
        try:
            icon = pygame.image.load(
                os.path.join(root, 'assets', 'sprites', 'car_player_2n.png'))
            pygame.display.set_icon(icon)
        except pygame.error:
            pass
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        # In hi-res mode the HUD and menus keep to the 320x200 grid on their
        # own layer, scaled up as one piece at present() time, so the bitmap
        # font stays exactly square instead of being re-rasterised.
        self.ui = (pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
                   if HIRES else self.screen)
        self._ui_scaled = (pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                           if HIRES else None)
        self.assets = Assets(root)
        self.renderer = Renderer(self.assets)
        self.scores = Scores(tracks.TRACK_SPECS)
        self.clock = pygame.time.Clock()
        self.rng = random.Random()

        self.track_cache = {}
        self.sel = 0
        self.car_sel = 0
        self.diff_sel = 0
        self.state = S_TITLE
        self.race = None
        self.demo = None
        self.demo_key = None
        self.fade = 1.0
        self.fade_dir = -1
        self.pending = None
        self.blink = 0.0
        self.name = [0, 0, 0]
        self.name_pos = 0
        self.result = None
        self.score_track = 0
        self.score_kind = 0
        self.score_level = 'easy'
        self.music_on = True
        self.running = True
        self.show_fps = False
        self.frame = 0
        self.race_end_timer = 0.0

        self.start_demo()
        self.audio.play_music('music_menu')

    # -- helpers --------------------------------------------------------
    def get_track(self, key):
        t = self.track_cache.get(key)
        if t is None:
            t = tracks.load(key)
            self.track_cache[key] = t
        return t

    def spec(self, i):
        return tracks.TRACK_SPECS[i % len(tracks.TRACK_SPECS)]

    def start_demo(self):
        if self.demo is not None:
            self.demo.clear()
        key = self.rng.choice([s['key'] for s in tracks.TRACK_SPECS])
        self.demo_key = key
        t = self.get_track(key)
        self.demo = Race(t, self.renderer, _SilentAudio(), self.scores,
                         random.Random(1))
        self.demo.state = Race.STATE_RACING
        self.demo.player.speed = MAX_SPEED * 0.7
        self.demo.time_left = 9999

    def transition(self, to, action=None):
        self.pending = (to, action)
        self.fade_dir = 1

    def set_state(self, s):
        self.state = s

    # -- main loop ------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.frame += 1
            self.blink += dt
            self.handle_events()
            self.update(dt)
            self.draw()
            self.present()
        self.audio.quiet()
        pygame.quit()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(
                (BASE_WIDTH * BASE_SCALE, BASE_HEIGHT * BASE_SCALE))

    def present(self):
        if self.ui is not self.screen:
            pygame.transform.scale(self.ui, (WIDTH, HEIGHT), self._ui_scaled)
            self.screen.blit(self._ui_scaled, (0, 0))
        ww, wh = self.window.get_size()
        k = min(ww / WIDTH, wh / HEIGHT)
        k = max(1, int(k)) if k >= 1 else k
        dw, dh = int(WIDTH * k), int(HEIGHT * k)
        if (dw, dh) != self.window.get_size():
            self.window.fill((0, 0, 0))
        scaled = pygame.transform.scale(self.screen, (dw, dh))
        self.window.blit(scaled, ((ww - dw) // 2, (wh - dh) // 2))
        pygame.display.flip()

    # -- input ----------------------------------------------------------
    def keymap(self):
        k = pygame.key.get_pressed()
        return {
            'left': k[pygame.K_LEFT] or k[pygame.K_a],
            'right': k[pygame.K_RIGHT] or k[pygame.K_d],
            'accel': k[pygame.K_UP] or k[pygame.K_w] or k[pygame.K_z],
            'brake': k[pygame.K_DOWN] or k[pygame.K_s] or k[pygame.K_x],
        }

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                self.on_key(e)

    def on_key(self, e):
        k = e.key
        mods = pygame.key.get_mods()
        if k == pygame.K_F1 or (k == pygame.K_f and (mods & pygame.KMOD_META)):
            self.toggle_fullscreen()
            return
        if k == pygame.K_q and (mods & pygame.KMOD_META):
            self.running = False
            return
        if k == pygame.K_m:
            self.music_on = not self.music_on
            self.audio.set_music_volume(0.55 if self.music_on else 0.0)
            return
        if k == pygame.K_F3:
            self.show_fps = not self.show_fps
            return
        handler = {
            S_TITLE: self.key_title, S_SELECT: self.key_select,
            S_DIFF: self.key_diff, S_CAR: self.key_car,
            S_RACE: self.key_race, S_PAUSE: self.key_pause,
            S_RESULT: self.key_result, S_NAME: self.key_name,
            S_SCORES: self.key_scores, S_HELP: self.key_help,
        }[self.state]
        handler(k)

    def key_title(self, k):
        if k in (pygame.K_ESCAPE,):
            self.running = False
        elif k == pygame.K_h:
            self.audio.play('sfx_blip')
            self.transition(S_SCORES)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play('sfx_select')
            self.transition(S_SELECT)

    def key_select(self, k):
        n = len(tracks.TRACK_SPECS)
        if k in (pygame.K_ESCAPE,):
            self.audio.play('sfx_blip')
            self.transition(S_TITLE)
        elif k in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
            self.sel = (self.sel - 1) % n
            self.audio.play('sfx_blip')
        elif k in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
            self.sel = (self.sel + 1) % n
            self.audio.play('sfx_blip')
        elif k == pygame.K_h:
            self.score_track = self.sel
            self.audio.play('sfx_blip')
            self.transition(S_SCORES)
        elif k in (pygame.K_i, pygame.K_SLASH):
            self.transition(S_HELP)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play('sfx_select')
            self.transition(S_DIFF)

    def key_diff(self, k):
        n = len(levels.LEVELS)
        if k == pygame.K_ESCAPE:
            self.audio.play('sfx_blip')
            self.transition(S_SELECT)
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
            self.diff_sel = (self.diff_sel - 1) % n
            self.audio.play('sfx_blip')
        elif k in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
            self.diff_sel = (self.diff_sel + 1) % n
            self.audio.play('sfx_blip')
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play('sfx_select')
            self.transition(S_CAR)

    def key_car(self, k):
        n = len(garage.CARS)
        if k == pygame.K_ESCAPE:
            self.audio.play('sfx_blip')
            self.transition(S_DIFF)
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
            self.car_sel = (self.car_sel - 1) % n
            self.audio.play('sfx_blip')
        elif k in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
            self.car_sel = (self.car_sel + 1) % n
            self.audio.play('sfx_blip')
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play('sfx_select')
            self.transition(S_RACE, 'start')

    def key_race(self, k):
        if k == pygame.K_ESCAPE or k == pygame.K_p:
            if self.race.state in (Race.STATE_RACING, Race.STATE_COUNTDOWN):
                self.audio.quiet()
                self.audio.play('sfx_blip')
                self.set_state(S_PAUSE)
        elif k == pygame.K_SPACE:
            self.race.use_turbo()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER) and \
                self.race.state in (Race.STATE_FINISHED, Race.STATE_TIMEUP):
            self.finish_race()

    def key_pause(self, k):
        if k in (pygame.K_ESCAPE, pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
            self.audio.play('sfx_blip')
            self.set_state(S_RACE)
        elif k == pygame.K_r:
            self.audio.play('sfx_select')
            self.transition(S_RACE, 'start')
        elif k == pygame.K_x:
            self.audio.play('sfx_blip')
            self.transition(S_SELECT, 'abandon')

    def key_result(self, k):
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                 pygame.K_ESCAPE):
            self.audio.play('sfx_select')
            if self.result and self.result['qualifies']:
                self.name = [0, 0, 0]
                self.name_pos = 0
                self.set_state(S_NAME)
            else:
                self.transition(S_SELECT, 'abandon')

    def key_name(self, k):
        if k in (pygame.K_LEFT,):
            self.name_pos = (self.name_pos - 1) % NAME_LEN
            self.audio.play('sfx_blip', 0.6)
        elif k in (pygame.K_RIGHT,):
            self.name_pos = (self.name_pos + 1) % NAME_LEN
            self.audio.play('sfx_blip', 0.6)
        elif k in (pygame.K_UP,):
            self.name[self.name_pos] = (self.name[self.name_pos] - 1) \
                % len(ALPHABET)
            self.audio.play('sfx_blip', 0.6)
        elif k in (pygame.K_DOWN,):
            self.name[self.name_pos] = (self.name[self.name_pos] + 1) \
                % len(ALPHABET)
            self.audio.play('sfx_blip', 0.6)
        elif k == pygame.K_BACKSPACE:
            self.name_pos = max(0, self.name_pos - 1)
            self.name[self.name_pos] = 0
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.commit_name()
        else:
            ch = pygame.key.name(k).upper()
            if len(ch) == 1 and ch in ALPHABET:
                self.name[self.name_pos] = ALPHABET.index(ch)
                self.audio.play('sfx_blip', 0.6)
                if self.name_pos == NAME_LEN - 1:
                    self.commit_name()
                else:
                    self.name_pos += 1

    def key_scores(self, k):
        n = len(tracks.TRACK_SPECS)
        if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_h):
            self.audio.play('sfx_blip')
            self.transition(S_SELECT)
        elif k in (pygame.K_LEFT, pygame.K_a):
            self.score_track = (self.score_track - 1) % n
            self.audio.play('sfx_blip')
        elif k in (pygame.K_RIGHT, pygame.K_d):
            self.score_track = (self.score_track + 1) % n
            self.audio.play('sfx_blip')
        elif k in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
            self.score_kind ^= 1
            self.audio.play('sfx_blip')
        elif k == pygame.K_d:
            keys = [lv['key'] for lv in levels.LEVELS]
            self.score_level = keys[(keys.index(self.score_level) + 1)
                                    % len(keys)]
            self.audio.play('sfx_blip')

    def key_help(self, k):
        self.audio.play('sfx_blip')
        self.transition(S_SELECT)

    # -- flow -----------------------------------------------------------
    def commit_name(self):
        text = ''.join(ALPHABET[i] for i in self.name)
        res = self.result
        placed = []
        if res['race_pos']:
            self.scores.insert(res['key'], 'race', text, res['race_time'],
                               res['car'], res['level'])
            placed.append('RACE')
        if res['lap_pos']:
            self.scores.insert(res['key'], 'lap', text, res['lap_time'],
                               res['car'], res['level'])
            placed.append('LAP')
        self.audio.play('sfx_select')
        self.score_track = self.sel
        self.score_kind = 0 if 'RACE' in placed else 1
        self.score_level = levels.BY_KEY[res['level']]['key']
        self.transition(S_SCORES, 'abandon')

    def begin_race(self):
        if self.race is not None:
            self.race.clear()
        if self.demo is not None:
            self.demo.clear()
            self.demo = None
        key = self.spec(self.sel)['key']
        t = self.get_track(key)
        self.race = Race(t, self.renderer, self.audio, self.scores, self.rng,
                         car=garage.CARS[self.car_sel],
                         level=levels.LEVELS[self.diff_sel])
        self.audio.play_music(t.theme['music'])
        self.result = None

    def abandon_race(self):
        if self.race is not None:
            self.race.clear()
            self.race = None
        self.audio.quiet()
        self.audio.play_music('music_menu')
        if self.demo is None:
            self.start_demo()

    def finish_race(self):
        r = self.race
        key = self.spec(self.sel)['key']
        completed = r.state == Race.STATE_FINISHED
        race_time = r.finished_at if completed else None
        lap_time = r.best_lap
        lk = r.level['key']
        race_pos = self.scores.position(key, 'race', race_time, lk) \
            if race_time else None
        lap_pos = self.scores.position(key, 'lap', lap_time, lk) \
            if lap_time else None
        self.result = {
            'key': key, 'name': r.track.name, 'completed': completed,
            'car': r.car['tag'], 'level': r.level['key'],
            'level_name': r.level['name'],
            'race_time': race_time, 'lap_time': lap_time,
            'race_pos': race_pos, 'lap_pos': lap_pos,
            'laps': list(r.lap_times), 'position': r.position,
            'field': r.rival_count + 1,
            'qualifies': bool(race_pos or lap_pos),
        }
        self.audio.quiet()
        self.set_state(S_RESULT)

    # -- update ---------------------------------------------------------
    def update(self, dt):
        if self.fade_dir > 0:
            self.fade = min(1.0, self.fade + dt * 4.0)
            if self.fade >= 1.0 and self.pending:
                to, action = self.pending
                self.pending = None
                if action == 'start':
                    self.begin_race()
                elif action == 'abandon':
                    self.abandon_race()
                if to in (S_TITLE, S_SELECT, S_SCORES, S_HELP) and \
                        self.demo is None:
                    self.start_demo()
                self.set_state(to)
                self.fade_dir = -1
        else:
            self.fade = max(0.0, self.fade - dt * 4.0)

        if self.state == S_RACE:
            self.race.update(dt, self.keymap())
            if self.race.state in (Race.STATE_FINISHED, Race.STATE_TIMEUP):
                self.race_end_timer += dt
                if self.race_end_timer > 3.4:
                    self.race_end_timer = 0.0
                    self.finish_race()
            else:
                self.race_end_timer = 0.0
        elif self.state == S_PAUSE:
            pass
        elif self.demo is not None:
            self.demo.update(dt, self.demo_input())
            if self.demo.player.total > self.demo.track.length * 1.4:
                self.start_demo()

    def demo_input(self):
        """Keeps a car circulating behind the menus."""
        return autopilot.drive(self.demo, skill=0.9)

    # -- draw -----------------------------------------------------------
    def draw(self):
        s = self.screen
        u = self.ui
        if u is not s:
            u.fill((0, 0, 0, 0))
        if self.state == S_RACE:
            self.race.draw(s, u)
        elif self.state == S_PAUSE:
            self.race.draw(s, u)
            self.overlay(u, 190)
            self.panel_title(u, 'PAUSED', 60)
            self.menu_lines(u, 92, [
                ('ENTER / ESC', 'RESUME'),
                ('R', 'RESTART RACE'),
                ('X', 'QUIT TO CIRCUITS'),
            ])
        else:
            if self.demo is not None:
                self._demo_world(s)
            else:
                s.fill((12, 12, 24))
            s = u
            if self.state == S_TITLE:
                self.draw_title(s)
            elif self.state == S_SELECT:
                self.draw_select(s)
            elif self.state == S_DIFF:
                self.draw_difficulty(s)
            elif self.state == S_CAR:
                self.draw_car_select(s)
            elif self.state == S_RESULT:
                self.draw_result(s)
            elif self.state == S_NAME:
                self.draw_name(s)
            elif self.state == S_SCORES:
                self.draw_scores(s)
            elif self.state == S_HELP:
                self.draw_help(s)

        if self.fade > 0.001:
            self.overlay(u, int(255 * self.fade), (0, 0, 0))
        if self.show_fps:
            pf.draw_text(u, '%d FPS' % int(self.clock.get_fps()), 2,
                         BASE_HEIGHT - 8, (120, 255, 120), 1)

    def _demo_world(self, s):
        d = self.demo
        r = self.renderer
        r.surface = s
        th = d.track.theme
        r.draw_background(th, d.sky_off, d.hill_off, d.tree_off, HEIGHT * 0.5 + 4)
        base_i, _ = r.draw_road(d.track, d.player.z, d.player.x, 1000, d.colors)
        r.draw_scene_sprites(d.track, base_i, d.colors, d.player, d.cars,
                             d._player_sprite(0))
        d._draw_weather(s)
        if th['ambient']:
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            tint.fill(th['ambient'])
            s.blit(tint, (0, 0))

    # -- widgets --------------------------------------------------------
    def overlay(self, s, alpha, colour=(6, 8, 20)):
        o = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        o.fill(colour + (alpha,))
        s.blit(o, (0, 0))

    def box(self, s, x, y, w, h, alpha=210, border=ACCENT):
        o = pygame.Surface((w, h), pygame.SRCALPHA)
        o.fill((10, 12, 28, alpha))
        s.blit(o, (x, y))
        pygame.draw.rect(s, border, (x, y, w, h), 1)

    def checker(self, s, y, h=4, phase=0):
        for i in range(0, s.get_width(), h):
            c = (240, 240, 240) if ((i // h) + phase) % 2 == 0 else (24, 24, 30)
            s.fill(c, (i, y, h, h))

    def panel_title(self, s, text, y, colour=ACCENT):
        pf.draw_text(s, text, BASE_WIDTH // 2, y, colour, 2, center=True,
                     shadow=(90, 20, 30))

    def menu_lines(self, s, y, rows, key_col=ACCENT, val_col=INK):
        for key, val in rows:
            pf.draw_text(s, key, 96, y, key_col, 1, right=True)
            pf.draw_text(s, val, 108, y, val_col, 1)
            y += 12

    # -- screens --------------------------------------------------------
    def draw_title(self, s):
        self.overlay(s, 120)
        self.checker(s, 22, 4, int(self.blink * 6) % 2)
        y = 34
        pf.draw_text(s, 'LATE', BASE_WIDTH // 2, y, (255, 236, 120), 5,
                     center=True, shadow=(150, 24, 40))
        pf.draw_text(s, 'APEX', BASE_WIDTH // 2, y + 40, (255, 236, 120), 5,
                     center=True, shadow=(150, 24, 40))
        self.checker(s, y + 78, 4, int(self.blink * 6) % 2 + 1)
        pf.draw_text(s, 'FIVE CIRCUITS - ONE CLOCK', BASE_WIDTH // 2, y + 90, INK, 1,
                     center=True)
        if int(self.blink * 2) % 2 == 0:
            pf.draw_text(s, 'PRESS ENTER TO RACE', BASE_WIDTH // 2, 158, ACCENT2, 2,
                         center=True, shadow=(60, 10, 20))
        pf.draw_text(s, 'H - HIGH SCORES', 5, BASE_HEIGHT - 9, DIM, 1)
        pf.draw_text(s, '(C) 198X', BASE_WIDTH - 5, BASE_HEIGHT - 9, DIM, 1, right=True)

    def draw_select(self, s):
        self.overlay(s, 175)
        self.checker(s, 0, 3, int(self.blink * 6) % 2)
        pf.draw_text(s, 'SELECT CIRCUIT', BASE_WIDTH // 2, 8, ACCENT, 2,
                     center=True, shadow=(90, 20, 30))
        y = 30
        for i, spec in enumerate(tracks.TRACK_SPECS):
            th = tracks.THEMES[spec['theme']]
            on = i == self.sel
            if on:
                self.box(s, 8, y - 3, BASE_WIDTH - 16, 22, 190, ACCENT)
            col = ACCENT if on else INK
            marker = '>' if on and int(self.blink * 3) % 2 == 0 else ' '
            pf.draw_text(s, '%s%s' % (marker, spec['name']), 14, y, col, 1)
            stars = '*' * tracks.DIFFICULTY[spec['key']]
            pf.draw_text(s, stars, BASE_WIDTH - 14, y, ACCENT2, 1, right=True)
            best = self.scores.best(spec['key'], 'race',
                                    levels.LEVELS[self.diff_sel]['key'])
            pf.draw_text(s, th['blurb'], 20, y + 9, DIM, 1)
            pf.draw_text(s, fmt(best), BASE_WIDTH - 14, y + 9, (150, 200, 255), 1,
                         right=True)
            y += 26
        pf.draw_text(s, 'ENTER RACE   H SCORES   I CONTROLS   ESC BACK',
                     BASE_WIDTH // 2, BASE_HEIGHT - 10, DIM, 1, center=True)

    def draw_difficulty(self, s):
        self.overlay(s, 205)
        self.checker(s, 0, 3, int(self.blink * 6) % 2)
        lv = levels.LEVELS[self.diff_sel]
        pf.draw_text(s, 'DIFFICULTY', BASE_WIDTH // 2, 8, ACCENT, 2,
                     center=True, shadow=(90, 20, 30))
        pf.draw_text(s, self.spec(self.sel)['name'], BASE_WIDTH // 2, 26, DIM,
                     1, center=True)

        y = 40
        for i, level in enumerate(levels.LEVELS):
            on = i == self.diff_sel
            if on:
                self.box(s, 10, y - 3, BASE_WIDTH - 20, 20, 190, ACCENT)
            col = ACCENT if on else INK
            marker = '>' if on and int(self.blink * 3) % 2 == 0 else ' '
            pf.draw_text(s, '%s%s' % (marker, level['name']), 16, y, col, 1)
            pf.draw_text(s, '*' * level['stars'], BASE_WIDTH - 16, y, ACCENT2,
                         1, right=True)
            pf.draw_text(s, level['blurb'], 22, y + 9, DIM, 1)
            y += 24

        # a little diagram of the road you are choosing
        mine, oncoming = levels.lanes_for(lv)
        cx, top, h = BASE_WIDTH // 2, 118, 46
        half = int(52 * lv['road'])
        s.fill((52, 52, 62), (cx - half, top, half * 2, h))
        s.fill((198, 40, 60), (cx - half - 3, top, 3, h))
        s.fill((198, 40, 60), (cx + half, top, 3, h))
        for c in levels.lane_centres(lv['lanes'])[:-1]:
            x = cx + int((c + 1.0 / lv['lanes']) * half)
            for yy in range(top + 3, top + h - 2, 7):
                s.fill((220, 220, 210), (x, yy, 1, 4))
        # direction arrows, drawn rather than lettered: the bitmap font has
        # no caret and would fall back to a question mark
        def arrow(x, y, up, colour):
            tip = y - 6 if up else y + 6
            pygame.draw.polygon(s, colour, [(x, tip), (x - 5, y), (x + 5, y)])
            s.fill(colour, (x - 2, y if up else y - 6, 4, 6))

        for c in mine:
            arrow(cx + int(c * half), top + h - 10, True, (120, 240, 140))
        for c in oncoming:
            arrow(cx + int(c * half), top + 10, False, (255, 110, 110))
        label = '%d LANES' % lv['lanes']
        if oncoming:
            label += '   %d ONCOMING' % len(oncoming)
        pf.draw_text(s, label, BASE_WIDTH // 2, top + h + 4, INK, 1,
                     center=True)
        pf.draw_text(s, 'CLOCK +%d%%' % round((lv['time'] - 1) * 100),
                     BASE_WIDTH // 2, top + h + 13, (150, 200, 255), 1,
                     center=True)

        pf.draw_text(s, 'UP/DOWN CHANGE   ENTER OK   ESC BACK',
                     BASE_WIDTH // 2, BASE_HEIGHT - 10, DIM, 1, center=True)

    def draw_car_select(self, s):
        self.overlay(s, 200)
        self.checker(s, 0, 3, int(self.blink * 6) % 2)
        car = garage.CARS[self.car_sel]
        pf.draw_text(s, 'CHOOSE YOUR CAR', BASE_WIDTH // 2, 8, ACCENT, 2,
                     center=True, shadow=(90, 20, 30))
        pf.draw_text(s, '%s - %s' % (self.spec(self.sel)['name'],
                                     levels.LEVELS[self.diff_sel]['name']),
                     BASE_WIDTH // 2, 26, DIM, 1, center=True)

        # the car itself, on a little stage
        img = self.assets.get('car_%s_2n' % car['key'])
        w = int(car['width'] * 1.25)
        h = int(img.get_height() * w / img.get_width())
        if h > 78:                       # the tall bodies must not run into
            h = 78                       # the heading above them
            w = int(img.get_width() * h / img.get_height())
        shown = self.assets.scaled('car_%s_2n' % car['key'], w, h)
        bob = math.sin(self.blink * 2.4) * 1.5
        s.fill((22, 24, 40), (BASE_WIDTH // 2 - 70, 118, 140, 3))
        s.blit(shown, (BASE_WIDTH // 2 - w // 2, int(118 - h + bob)))

        pf.draw_text(s, '<', 18, 74, ACCENT if int(self.blink * 3) % 2 == 0
                     else DIM, 2)
        pf.draw_text(s, '>', BASE_WIDTH - 28, 74, ACCENT
                     if int(self.blink * 3) % 2 == 0 else DIM, 2)

        pf.draw_text(s, car['name'], BASE_WIDTH // 2, 124, ACCENT, 2, center=True,
                     shadow=(60, 12, 24))
        pf.draw_text(s, car['blurb'], BASE_WIDTH // 2, 140, INK, 1, center=True)

        # stat bars
        x0, y = 92, 152
        for label, value in garage.stat_bars(car):
            pf.draw_text(s, label, x0 - 6, y, DIM, 1, right=True)
            bw = 128
            s.fill((38, 40, 56), (x0, y, bw, 5))
            n = max(2, int(bw * max(0.0, min(1.0, value))))
            for i in range(n):
                t = i / float(bw)
                col = (90, 220, 110) if t < 0.55 else (
                    (255, 210, 70) if t < 0.8 else (255, 120, 60))
                s.fill(col, (x0 + i, y, 1, 5))
            y += 9

        for i in range(len(garage.CARS)):
            x = BASE_WIDTH // 2 - len(garage.CARS) * 5 + i * 10
            s.fill(ACCENT if i == self.car_sel else (70, 74, 96),
                   (x, BASE_HEIGHT - 19, 6, 3))
        pf.draw_text(s, 'LEFT/RIGHT CHANGE   ENTER GO   ESC BACK',
                     BASE_WIDTH // 2, BASE_HEIGHT - 10, DIM, 1, center=True)

    def draw_result(self, s):
        self.overlay(s, 205)
        r = self.result
        ok = r['completed']
        self.checker(s, 0, 3, int(self.blink * 6) % 2)
        pf.draw_text(s, 'RACE COMPLETE' if ok else 'OUT OF TIME', BASE_WIDTH // 2,
                     12, (140, 255, 160) if ok else ACCENT2, 2, center=True,
                     shadow=(60, 12, 24))
        pf.draw_text(s, '%s - %s' % (r['name'], r['level_name']),
                     BASE_WIDTH // 2, 30, INK, 1, center=True)
        y = 46
        for i, lt in enumerate(r['laps']):
            best = (r['lap_time'] is not None and abs(lt - r['lap_time']) < 1e-6)
            pf.draw_text(s, 'LAP %d' % (i + 1), 96, y, DIM, 1, right=True)
            pf.draw_text(s, fmt(lt), 108, y, ACCENT if best else INK, 1)
            if best:
                pf.draw_text(s, 'BEST', 190, y, (140, 255, 160), 1)
            y += 11
        y += 4
        if ok:
            pf.draw_text(s, 'TOTAL', 96, y, DIM, 1, right=True)
            pf.draw_text(s, fmt(r['race_time']), 108, y, ACCENT, 2)
            y += 18
        pf.draw_text(s, 'FINISHED %d%s OF %d' % (
            r['position'], _ordinal(r['position']), r['field']),
            BASE_WIDTH // 2, y, INK, 1, center=True)
        y += 16
        if r['qualifies']:
            what = []
            if r['race_pos']:
                what.append('RACE #%d' % r['race_pos'])
            if r['lap_pos']:
                what.append('LAP #%d' % r['lap_pos'])
            if int(self.blink * 3) % 2 == 0:
                pf.draw_text(s, 'NEW RECORD - ' + '  '.join(what), BASE_WIDTH // 2,
                             y, ACCENT2, 1, center=True)
        pf.draw_text(s, 'PRESS ENTER', BASE_WIDTH // 2, BASE_HEIGHT - 12, DIM, 1,
                     center=True)

    def draw_name(self, s):
        self.overlay(s, 215)
        self.checker(s, 0, 3, int(self.blink * 6) % 2)
        pf.draw_text(s, 'NEW HIGH SCORE', BASE_WIDTH // 2, 22, ACCENT, 2,
                     center=True, shadow=(90, 20, 30))
        r = self.result
        line = []
        if r['race_pos']:
            line.append('RACE %s  #%d' % (fmt(r['race_time']), r['race_pos']))
        if r['lap_pos']:
            line.append('LAP %s  #%d' % (fmt(r['lap_time']), r['lap_pos']))
        y = 46
        for t in line:
            pf.draw_text(s, t, BASE_WIDTH // 2, y, INK, 1, center=True)
            y += 11
        pf.draw_text(s, 'ENTER YOUR INITIALS', BASE_WIDTH // 2, 76, DIM, 1,
                     center=True)
        total_w = NAME_LEN * 34
        x0 = BASE_WIDTH // 2 - total_w // 2
        for i in range(NAME_LEN):
            x = x0 + i * 34
            sel = i == self.name_pos
            col = ACCENT if sel else INK
            self.box(s, x, 92, 28, 34, 190, col if sel else (70, 74, 96))
            pf.draw_text(s, ALPHABET[self.name[i]], x + 14, 98, col, 4,
                         center=True)
            if sel and int(self.blink * 3) % 2 == 0:
                pf.draw_text(s, '^', x + 14, 130, ACCENT, 1, center=True)
        pf.draw_text(s, 'UP/DOWN LETTER   LEFT/RIGHT MOVE   ENTER OK',
                     BASE_WIDTH // 2, BASE_HEIGHT - 22, DIM, 1, center=True)
        pf.draw_text(s, 'OR JUST TYPE', BASE_WIDTH // 2, BASE_HEIGHT - 12, DIM, 1,
                     center=True)

    def draw_scores(self, s):
        self.overlay(s, 215)
        self.checker(s, 0, 3, int(self.blink * 6) % 2)
        spec = self.spec(self.score_track)
        kind = 'race' if self.score_kind == 0 else 'lap'
        level = levels.get(self.score_level)
        pf.draw_text(s, 'HALL OF FAME', BASE_WIDTH // 2, 10, ACCENT, 2, center=True,
                     shadow=(90, 20, 30))
        pf.draw_text(s, '< %s >' % spec['name'], BASE_WIDTH // 2, 28, INK, 1,
                     center=True)
        pf.draw_text(s, 'BEST %s TIMES  -  %s' % (kind.upper(), level['name']),
                     BASE_WIDTH // 2, 39, (150, 200, 255), 1, center=True)
        rows = self.scores.table(spec['key'], kind, level['key'])
        y = 52
        for i, row in enumerate(rows[:TABLE_SIZE]):
            col = ACCENT if i == 0 else INK
            pf.draw_text(s, '%d' % (i + 1), 78, y, DIM, 1, right=True)
            pf.draw_text(s, row['name'], 92, y, col, 1)
            if row.get('car'):
                pf.draw_text(s, row['car'], 132, y, (130, 140, 170), 1)
            pf.draw_text(s, fmt(row['time']), BASE_WIDTH - 84, y, col, 1, right=True)
            y += 13
        pf.draw_text(s, 'L/R CIRCUIT  U/D RACE-LAP  D DIFFICULTY  ESC BACK',
                     BASE_WIDTH // 2, BASE_HEIGHT - 10, DIM, 1, center=True)

    def draw_help(self, s):
        self.overlay(s, 215)
        pf.draw_text(s, 'CONTROLS', BASE_WIDTH // 2, 14, ACCENT, 2, center=True,
                     shadow=(90, 20, 30))
        self.menu_lines(s, 40, [
            ('UP / W', 'ACCELERATE'),
            ('DOWN / S', 'BRAKE'),
            ('LEFT RIGHT', 'STEER'),
            ('SPACE', 'TURBO BOOST (3 PER RACE)'),
            ('P / ESC', 'PAUSE'),
            ('M', 'MUSIC ON / OFF'),
            ('F1', 'FULLSCREEN'),
        ])
        pf.draw_text(s, 'BEAT THE CLOCK - EVERY LAP BUYS MORE TIME',
                     BASE_WIDTH // 2, 140, (150, 200, 255), 1, center=True)
        pf.draw_text(s, 'PRESS ANY KEY', BASE_WIDTH // 2, BASE_HEIGHT - 12, DIM, 1,
                     center=True)


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        return 'TH'
    return {1: 'ST', 2: 'ND', 3: 'RD'}.get(n % 10, 'TH')


class _SilentAudio:
    """Stand-in so the attract-mode demo makes no noise."""
    ok = False

    def play(self, *a, **k):
        pass

    def engine(self, *a, **k):
        pass

    def engine_off(self):
        pass

    def skid(self, *a, **k):
        pass

    def play_music(self, *a, **k):
        pass

    def quiet(self):
        pass
