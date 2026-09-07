"""Track geometry and the five themed circuits.

The road is a list of short segments, each with a curve amount and a world Y.
That is the classic pseudo-3D layout used by the 8/16-bit racers: the renderer
walks the list from the camera outwards and projects each segment's near and
far edge.
"""

import math
import random

SEGMENT_LENGTH = 200
RUMBLE_LENGTH = 3
ROAD_WIDTH = 2000
LANES = 3

LENGTHS = {'short': 16, 'medium': 30, 'long': 56, 'xlong': 88}
CURVES = {'easy': 2.0, 'medium': 4.0, 'hard': 6.5, 'vhard': 9.0}
# Crest heights. HILL_SCALE turns them into world units: at 1.0 the whole of
# Alpine Crest rose by less than two metres, which is invisible from the
# cockpit. Real mountain roads run at 6-10% gradient.
HILL_SCALE = 6.0
HILLS = {'low': 20, 'medium': 45, 'high': 75, 'huge': 110}


class Point:
    __slots__ = ('wx', 'wy', 'wz', 'cz', 'sx', 'sy', 'sw', 'scale')

    def __init__(self, wx, wy, wz):
        self.wx, self.wy, self.wz = wx, wy, wz
        self.cz = 0.0
        self.sx = self.sy = self.sw = 0.0
        self.scale = 0.0


class Segment:
    __slots__ = ('index', 'p1', 'p2', 'curve', 'sprites', 'cars', 'dark',
                 'looped', 'fog_i', 'clip', 'special')

    def __init__(self, index, y1, y2, curve):
        self.index = index
        self.p1 = Point(0.0, y1, index * SEGMENT_LENGTH)
        self.p2 = Point(0.0, y2, (index + 1) * SEGMENT_LENGTH)
        self.curve = curve
        self.sprites = []      # (offset, name, scale, collides)
        self.cars = []
        self.dark = (index // RUMBLE_LENGTH) % 2 == 1
        self.looped = False
        self.fog_i = 0
        self.clip = 0.0
        self.special = None    # 'start' band, etc.


def ease_in(a, b, p):
    return a + (b - a) * p * p


def ease_out(a, b, p):
    return a + (b - a) * (1 - (1 - p) ** 2)


def ease_in_out(a, b, p):
    return a + (b - a) * (-math.cos(p * math.pi) / 2 + 0.5)


# --------------------------------------------------------------------------
# Themes
# --------------------------------------------------------------------------

THEMES = {
    'city': {
        'title': 'NEON CITY',
        'blurb': 'DUSK IN THE DOWNTOWN GRID',
        'bg': 'city',
        'fog_color': (26, 22, 46),
        'fog_density': 4.2,
        'road': ((62, 62, 72), (56, 56, 66)),
        'grass': ((44, 46, 62), (40, 42, 58)),
        'rumble': ((196, 40, 56), (232, 232, 236)),
        'lane': (226, 226, 214),
        'grip': 1.0,
        'weather': None,
        'ambient': (255, 190, 120, 26),
        'scenery': [('obj_building0', 4.6, 1, 2.0, 4.6, 3),
                    ('obj_building1', 5.0, 1, 2.2, 4.8, 3),
                    ('obj_building2', 4.4, 1, 2.0, 4.4, 3),
                    ('obj_building3', 4.8, 1, 2.4, 5.0, 3),
                    ('obj_building4', 4.6, 1, 2.0, 4.6, 3),
                    ('obj_streetlamp', 1.3, 0, 1.16, 1.30, 4),
                    ('obj_billboard0', 1.7, 0, 1.5, 2.4),
                    ('obj_billboard1', 1.7, 0, 1.5, 2.4),
                    ('obj_billboard2', 1.7, 0, 1.5, 2.4)],
        'close': [('obj_cone', 0.6, 1.05, 1.16),
                  ('obj_tyrewall', 1.0, 1.06, 1.14)],
        'density': 0.40,
    },
    'country': {
        'title': 'GREEN VALLEY',
        'blurb': 'ROLLING HILLS AND LONG STRAIGHTS',
        'bg': 'country',
        'fog_color': (176, 208, 226),
        'fog_density': 3.0,
        'road': ((104, 104, 112), (96, 96, 104)),
        'grass': ((84, 158, 76), (74, 146, 68)),
        'rumble': ((228, 228, 232), (208, 56, 56)),
        'lane': (238, 238, 232),
        'grip': 1.0,
        'weather': None,
        'ambient': None,
        'scenery': [('obj_tree_oak', 2.4, 1, 1.45, 4.2, 4),
                    ('obj_tree_round', 2.0, 1, 1.45, 4.2, 4),
                    ('obj_bush', 1.2, 0, 1.20, 3.0, 3),
                    ('obj_haybale', 1.2, 1, 1.40, 3.4, 2),
                    ('obj_barn', 3.0, 1, 2.20, 4.6, 1),
                    ('obj_fence', 1.4, 0, 1.14, 1.34, 3)],
        'close': [('obj_fence', 1.4, 1.12, 1.26),
                  ('obj_bush', 1.0, 1.14, 1.30)],
        'density': 0.36,
    },
    'desert': {
        'title': 'DUST HIGHWAY',
        'blurb': 'FLAT OUT ACROSS THE BADLANDS',
        'bg': 'desert',
        'fog_color': (238, 208, 158),
        'fog_density': 2.4,
        'road': ((118, 112, 108), (110, 104, 100)),
        'grass': ((226, 188, 128), (214, 176, 118)),
        'rumble': ((232, 232, 226), (188, 76, 46)),
        'lane': (240, 236, 220),
        'grip': 0.94,
        'weather': 'dust',
        'ambient': (255, 226, 150, 20),
        'scenery': [('obj_cactus_big', 2.0, 1, 1.45, 4.4, 4),
                    ('obj_cactus_small', 1.5, 1, 1.30, 4.0, 4),
                    ('obj_rock_sand', 1.8, 1, 1.45, 4.2, 3),
                    ('obj_rock_small', 1.3, 1, 1.25, 3.4, 3),
                    ('obj_palm', 2.4, 1, 1.60, 4.4, 2),
                    ('obj_skull', 0.7, 0, 1.15, 2.2, 1),
                    ('obj_billboard2', 1.7, 0, 1.5, 2.6)],
        'close': [('obj_rock_small', 1.0, 1.10, 1.22),
                  ('obj_skull', 0.6, 1.06, 1.18)],
        'density': 0.28,
    },
    'winter': {
        'title': 'FROST PASS',
        'blurb': 'ICE, SNOW AND NO ROOM FOR ERROR',
        'bg': 'winter',
        'fog_color': (216, 226, 240),
        'fog_density': 5.0,
        'road': ((132, 138, 150), (124, 130, 142)),
        'grass': ((234, 240, 250), (220, 228, 242)),
        'rumble': ((214, 60, 60), (238, 244, 252)),
        'lane': (236, 242, 250),
        'grip': 0.80,
        'weather': 'snow',
        'ambient': (200, 220, 255, 22),
        'scenery': [('obj_pine_snow', 2.5, 1, 1.50, 4.2, 5),
                    ('obj_pine_snow_small', 1.9, 1, 1.35, 3.8, 4),
                    ('obj_rock_snow', 2.0, 1, 1.45, 4.0, 2),
                    ('obj_snowbank', 1.6, 0, 1.10, 1.40, 3),
                    ('obj_chalet', 2.8, 1, 2.20, 4.6, 1),
                    ('obj_snowpole', 0.9, 0, 1.08, 1.20, 3)],
        'close': [('obj_snowpole', 0.9, 1.07, 1.16),
                  ('obj_snowbank', 1.3, 1.08, 1.30)],
        'density': 0.38,
    },
    'summer': {
        'title': 'ALPINE CREST',
        'blurb': 'HIGH PEAKS AND HUGE CRESTS',
        'bg': 'summer',
        'fog_color': (150, 196, 240),
        'fog_density': 3.4,
        'road': ((100, 100, 108), (92, 92, 100)),
        'grass': ((92, 150, 84), (80, 138, 76)),
        'rumble': ((236, 236, 240), (60, 130, 214)),
        'lane': (240, 240, 234),
        'grip': 0.96,
        'weather': None,
        'ambient': None,
        'scenery': [('obj_pine', 2.5, 1, 1.45, 4.2, 5),
                    ('obj_pine_small', 1.9, 1, 1.35, 3.8, 4),
                    ('obj_rock_grey', 2.2, 1, 1.45, 4.0, 2),
                    ('obj_chalet', 2.8, 1, 2.20, 4.6, 1),
                    ('obj_tree_round', 1.8, 1, 1.40, 3.6, 3),
                    ('obj_tyrewall', 1.0, 1, 1.06, 1.16, 2)],
        'close': [('obj_tyrewall', 1.0, 1.06, 1.14),
                  ('obj_pine_small', 1.5, 1.20, 1.40)],
        'density': 0.34,
    },
}


# --------------------------------------------------------------------------
# Track building
# --------------------------------------------------------------------------

class Track:
    def __init__(self, key, spec):
        self.key = key
        self.theme = THEMES[spec['theme']]
        self.name = spec['name']
        self.laps = spec.get('laps', 3)
        self.start_time = spec['start_time']
        self.lap_bonus = spec['lap_bonus']
        self.rivals = spec.get('rivals', 8)
        self.par_speed = spec.get('par_speed', 1.0)
        self.segments = []
        self._last_y = 0.0
        spec['build'](self)
        self._close_loop()
        self.length = len(self.segments) * SEGMENT_LENGTH
        self._decorate(spec.get('seed', 1))

    # -- geometry -------------------------------------------------------
    def _add(self, curve, y):
        i = len(self.segments)
        self.segments.append(Segment(i, self._last_y, y, curve))
        self._last_y = y

    def road(self, enter, hold, leave, curve=0.0, hill=0.0):
        start_y = self._last_y
        end_y = start_y + hill * SEGMENT_LENGTH / 200.0 * 2.0 * HILL_SCALE
        total = enter + hold + leave
        for n in range(enter):
            self._add(ease_in(0, curve, n / enter),
                      ease_in_out(start_y, end_y, n / total))
        for n in range(hold):
            self._add(curve, ease_in_out(start_y, end_y, (enter + n) / total))
        for n in range(leave):
            self._add(ease_in_out(curve, 0, n / leave),
                      ease_in_out(start_y, end_y, (enter + hold + n) / total))

    def straight(self, length='medium'):
        n = LENGTHS[length]
        self.road(n, n, n, 0, 0)

    def curve(self, length='medium', curve='medium', hill=0.0):
        n = LENGTHS[length]
        self.road(n, n, n, CURVES[curve] if isinstance(curve, str) else curve,
                  hill)

    def hill(self, length='medium', height='medium'):
        n = LENGTHS[length]
        self.road(n, n, n, 0, HILLS[height] if isinstance(height, str)
                  else height)

    def s_curves(self, scale=1.0):
        self.road(LENGTHS['short'], LENGTHS['short'], LENGTHS['short'],
                  -CURVES['easy'] * scale, 0)
        self.road(LENGTHS['medium'], LENGTHS['medium'], LENGTHS['medium'],
                  CURVES['medium'] * scale, HILLS['medium'] * 0.4)
        self.road(LENGTHS['medium'], LENGTHS['medium'], LENGTHS['medium'],
                  CURVES['easy'] * scale, -HILLS['low'] * 0.4)
        self.road(LENGTHS['short'], LENGTHS['short'], LENGTHS['short'],
                  -CURVES['easy'] * scale, HILLS['medium'] * 0.4)
        self.road(LENGTHS['medium'], LENGTHS['medium'], LENGTHS['medium'],
                  -CURVES['medium'] * scale, -HILLS['medium'] * 0.4)

    def bumps(self):
        for h in (5, -3, 4, -5, 3, -4, 5, -3):
            self.road(10, 10, 10, 0, h)

    def _close_loop(self):
        """Flatten the last stretch back to y=0 so the lap joins seamlessly.

        The run-out is as long as the drop needs: a fixed length turned the
        closure into the steepest ramp on the circuit once the hills were
        scaled up.
        """
        drop = abs(self._last_y)
        needed = int(drop / (SEGMENT_LENGTH * 0.035)) + 1
        tail = min(max(120, needed), int(len(self.segments) * 0.4))
        tail = min(tail, len(self.segments))
        start = len(self.segments) - tail
        y0 = self.segments[start].p1.wy
        for k in range(tail):
            seg = self.segments[start + k]
            t = k / tail
            seg.p1.wy = ease_in_out(y0, 0.0, t)
            seg.p2.wy = ease_in_out(y0, 0.0, min(1.0, (k + 1) / tail))
            seg.curve *= (1.0 - t)
        # pad to a multiple of the rumble stripe so colours line up on the loop
        while len(self.segments) % (RUMBLE_LENGTH * 2):
            self._add(0.0, 0.0)

    # -- dressing -------------------------------------------------------
    def _decorate(self, seed):
        rng = random.Random(seed)
        th = self.theme
        n = len(self.segments)
        pool = th['scenery']

        # Start/finish: the chequered tarmac straddles the line and the gantry
        # sits just before it, so you pass under it on the way to the flag
        # rather than starting nose-to-leg with it.
        self.segments[n - 7].sprites.append((0.0, 'obj_gantry', 2.2, False))
        for k in range(6):
            self.segments[k].special = 'start'
            self.segments[n - 1 - k].special = 'start'

        weighted = []
        for entry in pool:
            weighted.extend([entry[:5]] * (entry[5] if len(entry) > 5 else 1))

        for i in range(12, n - 12):
            seg = self.segments[i]
            if rng.random() < th['density']:
                name, sc, collides, o0, o1 = rng.choice(weighted)
                side = -1 if rng.random() < 0.5 else 1
                seg.sprites.append((side * rng.uniform(o0, o1), name,
                                    sc * rng.uniform(0.88, 1.12),
                                    bool(collides)))
            # roadside furniture hugging the tarmac
            if i % 20 == 0 and rng.random() < 0.6:
                name, sc, o0, o1 = rng.choice(th['close'])
                side = -1 if rng.random() < 0.5 else 1
                seg.sprites.append((side * rng.uniform(o0, o1), name, sc, True))
            # warning chevrons before a real corner
            if i % 12 == 0 and abs(seg.curve) > 2.5:
                tag = 'obj_sign_r' if seg.curve > 0 else 'obj_sign_l'
                side = 1 if seg.curve > 0 else -1
                self.segments[max(0, i - 40)].sprites.append(
                    (side * 1.30, tag, 1.5, False))

    # -- queries --------------------------------------------------------
    def segment_at(self, z):
        return self.segments[int(z / SEGMENT_LENGTH) % len(self.segments)]


# --------------------------------------------------------------------------
# The five circuits
# --------------------------------------------------------------------------

def _build_city(t):
    t.straight('short')
    t.curve('medium', 'medium', 10)
    t.hill('short', 'low')
    t.straight('medium')
    t.curve('short', 'hard')
    t.curve('short', -CURVES['hard'])
    t.straight('short')
    t.curve('medium', -CURVES['medium'], 12)
    t.straight('medium')
    t.curve('short', 'vhard')
    t.straight('short')
    t.curve('medium', -CURVES['easy'], -10)
    t.bumps()
    t.curve('short', -CURVES['vhard'])
    t.straight('medium')
    t.curve('medium', 'easy', 14)
    t.curve('short', -CURVES['hard'])
    t.straight('long')
    t.curve('medium', 'hard')
    t.curve('medium', -CURVES['medium'], -18)
    t.hill('short', 'medium')
    t.straight('medium')


def _build_country(t):
    t.straight('long')
    t.curve('long', 'easy', 18)
    t.straight('medium')
    t.hill('medium', 'medium')
    t.curve('medium', -CURVES['medium'])
    t.straight('long')
    t.curve('medium', 'medium', -20)
    t.s_curves(0.8)
    t.straight('xlong')
    t.curve('long', -CURVES['easy'], 26)
    t.straight('medium')
    t.curve('medium', 'hard')
    t.hill('medium', 'low')
    t.curve('long', -CURVES['medium'], -18)
    t.straight('long')
    t.curve('medium', 'easy')
    t.straight('medium')


def _build_desert(t):
    t.straight('xlong')
    t.curve('long', 'easy', 14)
    t.hill('long', 'medium')
    t.straight('long')
    t.curve('long', -CURVES['easy'], 12)
    t.straight('long')
    t.curve('medium', 'medium')
    t.straight('xlong')
    t.curve('long', -CURVES['medium'], -14)
    t.straight('long')
    t.curve('medium', 'hard')
    t.straight('xlong')
    t.curve('long', 'easy', 16)
    t.straight('long')
    t.curve('medium', -CURVES['hard'], -20)
    t.hill('medium', 'low')
    t.straight('long')


def _build_winter(t):
    t.straight('short')
    t.curve('short', 'hard', 16)
    t.curve('short', -CURVES['hard'], -10)
    t.straight('short')
    t.curve('medium', 'vhard', 22)
    t.straight('short')
    t.curve('short', -CURVES['vhard'])
    t.hill('short', 'high')
    t.curve('medium', 'medium', -26)
    t.curve('short', -CURVES['hard'], 18)
    t.straight('medium')
    t.s_curves(1.25)
    t.curve('short', 'vhard', -20)
    t.straight('short')
    t.curve('medium', -CURVES['medium'], 24)
    t.bumps()
    t.curve('short', 'hard')
    t.curve('short', -CURVES['hard'], -16)
    t.straight('medium')


def _build_summer(t):
    t.straight('medium')
    t.hill('medium', 'huge')
    t.curve('medium', 'medium', -40)
    t.straight('short')
    t.curve('long', -CURVES['medium'], 34)
    t.straight('medium')
    t.hill('short', 'high')
    t.curve('medium', 'hard', -30)
    t.s_curves(1.0)
    t.straight('long')
    t.curve('medium', -CURVES['hard'], 28)
    t.hill('medium', 'medium')
    t.curve('long', 'easy', -34)
    t.straight('medium')
    t.curve('medium', 'vhard')
    t.straight('long')
    t.curve('medium', -CURVES['easy'], 20)
    t.straight('medium')


TRACK_SPECS = [
    dict(key='country', name='GREEN VALLEY', theme='country',
         build=_build_country, start_time=61, lap_bonus=44, rivals=8,
         seed=101, par_speed=1.00),
    dict(key='city', name='NEON CITY', theme='city',
         build=_build_city, start_time=49, lap_bonus=36, rivals=9,
         seed=202, par_speed=0.98),
    dict(key='desert', name='DUST HIGHWAY', theme='desert',
         build=_build_desert, start_time=73, lap_bonus=51, rivals=8,
         seed=303, par_speed=1.04),
    dict(key='summer', name='ALPINE CREST', theme='summer',
         build=_build_summer, start_time=53, lap_bonus=40, rivals=8,
         seed=404, par_speed=0.99),
    dict(key='winter', name='FROST PASS', theme='winter',
         build=_build_winter, start_time=49, lap_bonus=36, rivals=7,
         seed=505, par_speed=0.93),
]

DIFFICULTY = {'country': 1, 'city': 2, 'desert': 2, 'summer': 3, 'winter': 4}


def load(key):
    for spec in TRACK_SPECS:
        if spec['key'] == key:
            return Track(key, spec)
    raise KeyError(key)
