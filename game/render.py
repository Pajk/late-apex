"""The pseudo-3D road renderer.

Everything is drawn into a 320x200 surface which the window then scales up,
so the game keeps a chunky 16-bit look no matter how big the window is.
"""

import math
import os

import pygame

from .config import BASE_HEIGHT, BASE_WIDTH, HIRES, SCALE
from .track import SEGMENT_LENGTH, ROAD_WIDTH, LANES

# The world renders at this size; the HUD keeps to the BASE_* grid and is
# scaled up as one piece so its pixels stay square.
WIDTH, HEIGHT = BASE_WIDTH * SCALE, BASE_HEIGHT * SCALE
FIELD_OF_VIEW = 100
CAMERA_HEIGHT = 1000
DRAW_DISTANCE = 210
FOG_STEPS = 12
# World size of a roadside sprite = image width * scale * OBJECT_SCALE units.
OBJECT_SCALE = 6.0

CAMERA_DEPTH = 1.0 / math.tan((FIELD_OF_VIEW / 2) * math.pi / 180)


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def sprite_anchor(offset, width):
    """Centre of a roadside sprite, in road half-widths.

    Sprites are anchored at their inner edge, so an offset reads as "where the
    object starts" and a row of trees lines up regardless of how wide each one
    is. An offset of exactly zero means centred across the road - that is what
    the start gantry uses, and treating it as a right-hand sprite is what once
    put one of its legs on the centre line.
    """
    if offset > 0:
        return offset + width / 2
    if offset < 0:
        return offset - width / 2
    return 0.0


def exponential_fog(distance, density):
    return 1.0 / (math.exp(distance * distance * density))


class Assets:
    """Loads the generated PNGs and caches every scaled + fogged variant."""

    def __init__(self, root):
        self.dir = os.path.join(root, 'assets', 'sprites')
        self.raw = {}
        self._cache = {}
        self._backdrops = {}
        for fn in os.listdir(self.dir):
            if fn.endswith('.png'):
                img = pygame.image.load(os.path.join(self.dir, fn))
                self.raw[fn[:-4]] = img.convert_alpha()

    def get(self, name):
        return self.raw[name]

    def backdrop(self, name):
        """A parallax layer at the current render scale (cached)."""
        if not HIRES:
            return self.raw[name]
        hit = self._backdrops.get(name)
        if hit is None:
            img = self.raw[name]
            hit = pygame.transform.scale(
                img, (img.get_width() * SCALE, img.get_height() * SCALE))
            self._backdrops[name] = hit
        return hit

    def scaled(self, name, w, h, fog_i=0, fog_color=(0, 0, 0)):
        w = max(1, int(w))
        h = max(1, int(h))
        if w > 4:                       # quantise so the cache stays small
            w -= w % 2
            h -= h % 2
        key = (name, w, h, fog_i)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        img = pygame.transform.scale(self.raw[name], (w, h))
        if fog_i:
            f = 1.0 - fog_i / float(FOG_STEPS)
            img = img.copy()
            k = int(f * 255)
            img.fill((k, k, k, 255), None, pygame.BLEND_RGBA_MULT)
            img.fill((int(fog_color[0] * (1 - f)), int(fog_color[1] * (1 - f)),
                      int(fog_color[2] * (1 - f)), 0), None,
                     pygame.BLEND_RGBA_ADD)
        if len(self._cache) > 6000:
            self._cache.clear()
        self._cache[key] = img
        return img


class ThemeColors:
    """Precomputes every road colour at every fog depth, so the per-frame
    render loop never has to blend colours in Python."""

    def __init__(self, theme):
        fog = theme['fog_color']
        self.fog_color = fog
        self.bands = []
        for i in range(DRAW_DISTANCE):
            f = exponential_fog(i / float(DRAW_DISTANCE), theme['fog_density'])
            t = 1.0 - f
            light = dict(
                road=mix(theme['road'][0], fog, t),
                grass=mix(theme['grass'][0], fog, t),
                rumble=mix(theme['rumble'][0], fog, t),
                lane=mix(theme['lane'], fog, t))
            dark = dict(
                road=mix(theme['road'][1], fog, t),
                grass=mix(theme['grass'][1], fog, t),
                rumble=mix(theme['rumble'][1], fog, t),
                lane=None)
            start = dict(
                road=mix((236, 236, 236), fog, t),
                grass=mix(theme['grass'][0], fog, t),
                rumble=mix((30, 30, 34), fog, t),
                lane=mix((30, 30, 34), fog, t))
            start_d = dict(
                road=mix((32, 32, 36), fog, t),
                grass=mix(theme['grass'][1], fog, t),
                rumble=mix((236, 236, 236), fog, t),
                lane=mix((236, 236, 236), fog, t))
            self.bands.append((light, dark, start, start_d))
        # fog index used for sprite tinting
        self.sprite_fog = []
        for i in range(DRAW_DISTANCE):
            f = exponential_fog(i / float(DRAW_DISTANCE), theme['fog_density'])
            self.sprite_fog.append(min(FOG_STEPS - 1,
                                       int((1.0 - f) * FOG_STEPS)))


def project(p, cam_x, cam_y, cam_z, road_width):
    p.cz = p.wz - cam_z
    if p.cz < 1:
        p.cz = 1
    p.scale = CAMERA_DEPTH / p.cz
    p.sx = WIDTH / 2 + p.scale * (p.wx - cam_x) * WIDTH / 2
    p.sy = HEIGHT / 2 - p.scale * (p.wy - cam_y) * HEIGHT / 2
    p.sw = p.scale * road_width * WIDTH / 2


def rumble_width(projected_width):
    return projected_width / max(6, 2 * LANES)


def lane_width(projected_width):
    return projected_width / max(32, 8 * LANES)


class Renderer:
    def __init__(self, assets):
        self.assets = assets
        self.surface = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.theme_cache = {}
        self.bg_cache = {}

    def colors_for(self, theme):
        tc = self.theme_cache.get(id(theme))
        if tc is None:
            tc = ThemeColors(theme)
            self.theme_cache[id(theme)] = tc
        return tc

    # -- backdrop -------------------------------------------------------
    def draw_background(self, theme, sky_off, hill_off, tree_off, horizon):
        s = self.surface
        a = self.assets
        bg = theme['bg']
        sky = a.backdrop('bg_%s_sky' % bg)
        far = a.backdrop('bg_%s_far' % bg)
        near = a.backdrop('bg_%s_near' % bg)

        base = int(horizon)
        s.fill(theme['fog_color'])
        sw = sky.get_width()
        x = -int(sky_off) % sw - sw
        y = base - sky.get_height()
        while x < WIDTH:
            s.blit(sky, (x, y))
            x += sw
        if y > 0:
            s.fill(theme['fog_color'], (0, 0, WIDTH, y))

        for layer, off, dy in ((far, hill_off, 0), (near, tree_off, 0)):
            lw = layer.get_width()
            x = -int(off) % lw - lw
            ly = base - layer.get_height() + dy
            while x < WIDTH:
                s.blit(layer, (x, ly))
                x += lw

    # -- road -----------------------------------------------------------
    def draw_road(self, track, position, player_x, camera_h, colors):
        s = self.surface
        segs = track.segments
        n_segs = len(segs)
        base_i = int(position / SEGMENT_LENGTH) % n_segs
        base = segs[base_i]
        base_pct = (position % SEGMENT_LENGTH) / SEGMENT_LENGTH

        # camera y follows the road surface
        cam_y = base.p1.wy + (base.p2.wy - base.p1.wy) * base_pct + camera_h
        maxy = HEIGHT
        x = 0.0
        dx = -(base.curve * base_pct)
        bands = colors.bands
        poly = pygame.draw.polygon
        drawn = []

        for i in range(DRAW_DISTANCE):
            seg = segs[(base_i + i) % n_segs]
            looped = (base_i + i) >= n_segs
            seg.looped = looped
            seg.fog_i = i
            seg.clip = maxy
            cz = position - (track.length if looped else 0)
            project(seg.p1, player_x * ROAD_WIDTH - x, cam_y, cz, ROAD_WIDTH)
            project(seg.p2, player_x * ROAD_WIDTH - x - dx, cam_y, cz,
                    ROAD_WIDTH)
            x += dx
            dx += seg.curve

            if seg.p1.cz <= CAMERA_DEPTH or seg.p2.sy >= seg.p1.sy \
                    or seg.p2.sy >= maxy:
                continue

            band = bands[i]
            if seg.special == 'start':
                col = band[3] if seg.dark else band[2]
            else:
                col = band[1] if seg.dark else band[0]

            x1, y1, w1 = seg.p1.sx, seg.p1.sy, seg.p1.sw
            x2, y2, w2 = seg.p2.sx, seg.p2.sy, seg.p2.sw

            # verge
            s.fill(col['grass'], (0, int(y2), WIDTH, int(y1 - y2) + 1))

            r1, r2 = rumble_width(w1), rumble_width(w2)
            poly(s, col['rumble'], ((x1 - w1 - r1, y1), (x1 - w1, y1),
                                    (x2 - w2, y2), (x2 - w2 - r2, y2)))
            poly(s, col['rumble'], ((x1 + w1 + r1, y1), (x1 + w1, y1),
                                    (x2 + w2, y2), (x2 + w2 + r2, y2)))
            poly(s, col['road'], ((x1 - w1, y1), (x1 + w1, y1),
                                  (x2 + w2, y2), (x2 - w2, y2)))
            if col['lane'] and w1 > 6:
                l1, l2 = lane_width(w1), lane_width(w2)
                lw1 = w1 * 2 / LANES
                lw2 = w2 * 2 / LANES
                lx1 = x1 - w1 + lw1
                lx2 = x2 - w2 + lw2
                for _ in range(LANES - 1):
                    poly(s, col['lane'], ((lx1 - l1, y1), (lx1 + l1, y1),
                                          (lx2 + l2, y2), (lx2 - l2, y2)))
                    lx1 += lw1
                    lx2 += lw2
            maxy = y1
            drawn.append(i)
        return base_i, drawn

    # -- sprites --------------------------------------------------------
    def draw_scene_sprites(self, track, base_i, colors, player, cars,
                           player_sprite):
        s = self.surface
        a = self.assets
        segs = track.segments
        n_segs = len(segs)
        fog_color = colors.fog_color
        sprite_fog = colors.sprite_fog
        player_seg_i = int(player.z / SEGMENT_LENGTH) % n_segs

        for i in range(DRAW_DISTANCE - 1, -1, -1):
            seg = segs[(base_i + i) % n_segs]
            if seg.p1.scale <= 0 or seg.p1.sw <= 0:
                continue
            fog_i = sprite_fog[i]
            if fog_i >= FOG_STEPS - 1:
                continue
            scale = seg.p1.scale
            sx, sy, sw = seg.p1.sx, seg.p1.sy, seg.p1.sw

            for car in seg.cars:
                img = a.get(car.sprite)
                cs = car.size * OBJECT_SCALE
                w = img.get_width() * scale * WIDTH / 2 * cs
                h = img.get_height() * scale * WIDTH / 2 * cs
                px = sx + scale * car.offset * ROAD_WIDTH * WIDTH / 2
                self._blit_sprite(img, car.sprite, px, sy, w, h, seg.clip,
                                  fog_i, fog_color)

            for offset, name, sc, _c in seg.sprites:
                img = a.get(name)
                ss = sc * OBJECT_SCALE
                w = img.get_width() * scale * WIDTH / 2 * ss
                h = img.get_height() * scale * WIDTH / 2 * ss
                centre = sprite_anchor(offset,
                                       img.get_width() * ss / ROAD_WIDTH)
                px = sx + scale * centre * ROAD_WIDTH * WIDTH / 2
                self._blit_sprite(img, name, px, sy, w, h, seg.clip, fog_i,
                                  fog_color)

            if (base_i + i) % n_segs == player_seg_i and player_sprite:
                s.blit(player_sprite[0], player_sprite[1])

    def _blit_sprite(self, img, name, cx, base_y, w, h, clip, fog_i, fog_color):
        if w < 1 or h < 1 or w > 2200 * SCALE:
            return
        x = cx - w / 2
        y = base_y - h
        if x > WIDTH or x + w < 0 or y > HEIGHT:
            return
        surf = self.assets.scaled(name, w, h, fog_i, fog_color)
        w, h = surf.get_size()
        clip_h = h
        if clip:
            clip_h = min(h, max(0, clip - y))
        if clip_h <= 0:
            return
        if clip_h < h:
            self.surface.blit(surf, (int(x), int(y)), (0, 0, w, int(clip_h)))
        else:
            self.surface.blit(surf, (int(x), int(y)))
