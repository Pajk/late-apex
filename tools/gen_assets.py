"""Generates every graphic in the game as a PNG. Nothing is hand-drawn or
downloaded: cars, scenery and parallax backdrops are all built from
primitives here so the whole look stays consistent and reproducible.

    python tools/gen_assets.py
"""
import os
import math
import random
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from game import pixelfont  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'sprites')


def surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def save(s, name):
    pygame.image.save(s, os.path.join(OUT, name + '.png'))
    return name


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def poly(s, color, pts):
    pygame.draw.polygon(s, color, pts)


def rect(s, color, x, y, w, h):
    if w > 0 and h > 0:
        s.fill(color, (int(x), int(y), int(w), int(h)))


# --------------------------------------------------------------------------
# Cars
# --------------------------------------------------------------------------

def draw_car(body, w=120, h=68, lean=0, braking=False, detail=True):
    """Rear view of a wedge-shaped 80s supercar. `lean` in -2..2 tilts the
    cabin and wheels so the car visibly rolls into a corner."""
    s = surf(w, h)
    cx = w / 2
    lo = lean * 3.0            # cabin slide
    tilt = lean * 1.6          # body roll
    dark = shade(body, 0.55)
    darker = shade(body, 0.35)
    light = shade(body, 1.25)
    tyre = (26, 26, 32)
    rim = (150, 152, 165)
    glass = (34, 40, 62)

    ground = h - 3
    # tyres
    for side in (-1, 1):
        wx = cx + side * (w * 0.44) - 11
        wy = ground - 21 + side * tilt * 0.6
        rect(s, tyre, wx, wy, 22, 21)
        rect(s, shade(tyre, 1.5), wx + 2, wy + 3, 18, 3)
        rect(s, rim, wx + 6, wy + 8, 10, 8)
        rect(s, shade(rim, 0.6), wx + 6, wy + 13, 10, 3)

    # shadow under the sills
    rect(s, (0, 0, 0, 120), cx - w * 0.42, ground - 2, w * 0.84, 4)

    # main body: low wide wedge
    body_pts = [
        (cx - w * 0.46, ground - 6 + tilt),
        (cx + w * 0.46, ground - 6 - tilt),
        (cx + w * 0.42, ground - 32 - tilt),
        (cx - w * 0.42, ground - 32 + tilt),
    ]
    poly(s, body, body_pts)
    # haunches highlight
    poly(s, light, [
        (cx - w * 0.42, ground - 32 + tilt),
        (cx + w * 0.42, ground - 32 - tilt),
        (cx + w * 0.40, ground - 28 - tilt),
        (cx - w * 0.40, ground - 28 + tilt),
    ])
    # rear valance
    poly(s, darker, [
        (cx - w * 0.44, ground - 6 + tilt),
        (cx + w * 0.44, ground - 6 - tilt),
        (cx + w * 0.40, ground - 13 - tilt),
        (cx - w * 0.40, ground - 13 + tilt),
    ])

    # cabin
    cab_top = ground - 50
    poly(s, dark, [
        (cx - w * 0.30 + lo, ground - 32 + tilt),
        (cx + w * 0.30 + lo, ground - 32 - tilt),
        (cx + w * 0.23 + lo, cab_top - tilt),
        (cx - w * 0.23 + lo, cab_top + tilt),
    ])
    # rear screen
    poly(s, glass, [
        (cx - w * 0.25 + lo, ground - 34 + tilt),
        (cx + w * 0.25 + lo, ground - 34 - tilt),
        (cx + w * 0.19 + lo, cab_top + 3 - tilt),
        (cx - w * 0.19 + lo, cab_top + 3 + tilt),
    ])
    poly(s, shade(glass, 1.9), [
        (cx - w * 0.19 + lo, cab_top + 3 + tilt),
        (cx + w * 0.02 + lo, cab_top + 3 - tilt),
        (cx - w * 0.10 + lo, ground - 34),
        (cx - w * 0.25 + lo, ground - 34 + tilt),
    ])

    if detail:
        # rear wing on struts
        wing_y = cab_top - 7
        for sx in (-0.20, 0.20):
            rect(s, darker, cx + sx * w + lo - 2, wing_y + 3, 4, 10)
        poly(s, shade(body, 0.8), [
            (cx - w * 0.40 + lo, wing_y + 5 + tilt),
            (cx + w * 0.40 + lo, wing_y + 5 - tilt),
            (cx + w * 0.40 + lo, wing_y - tilt),
            (cx - w * 0.40 + lo, wing_y + tilt),
        ])
        poly(s, light, [
            (cx - w * 0.40 + lo, wing_y + 1 + tilt),
            (cx + w * 0.40 + lo, wing_y + 1 - tilt),
            (cx + w * 0.40 + lo, wing_y - tilt),
            (cx - w * 0.40 + lo, wing_y + tilt),
        ])

    # tail lights
    lamp = (255, 70, 50) if not braking else (255, 200, 160)
    glow = (255, 160, 120) if not braking else (255, 255, 220)
    for side in (-1, 1):
        lx = cx + side * w * 0.27 - 11
        ly = ground - 27 - side * tilt * 0.5
        rect(s, shade(lamp, 0.5), lx, ly, 22, 9)
        rect(s, lamp, lx + 1, ly + 1, 20, 7)
        rect(s, glow, lx + 3, ly + 2, 16, 3)
    # plate + exhaust
    rect(s, (222, 222, 210), cx - 9, ground - 15, 18, 7)
    rect(s, (40, 40, 44), cx - 7, ground - 13, 14, 3)
    for side in (-1, 1):
        rect(s, (60, 62, 70), cx + side * 16 - 4, ground - 6, 8, 4)
    return s


def _wheels(s, w, h, cx, ground, tilt, span=0.44, size=(22, 21)):
    tyre = (26, 26, 32)
    rim = (150, 152, 165)
    ww, wh = size
    for side in (-1, 1):
        wx = cx + side * (w * span) - ww / 2
        wy = ground - wh + side * tilt * 0.6
        rect(s, tyre, wx, wy, ww, wh)
        rect(s, shade(tyre, 1.5), wx + 2, wy + 3, ww - 4, 3)
        rect(s, rim, wx + ww * 0.27, wy + wh * 0.38, ww * 0.45, wh * 0.38)
        rect(s, shade(rim, 0.6), wx + ww * 0.27, wy + wh * 0.62, ww * 0.45,
             wh * 0.14)


def _lamps(s, cx, y, spread, lamp_w, braking, tilt=0.0):
    lamp = (255, 70, 50) if not braking else (255, 200, 160)
    glow = (255, 160, 120) if not braking else (255, 255, 220)
    for side in (-1, 1):
        lx = cx + side * spread - lamp_w / 2
        ly = y - side * tilt * 0.5
        rect(s, shade(lamp, 0.5), lx, ly, lamp_w, 9)
        rect(s, lamp, lx + 1, ly + 1, lamp_w - 2, 7)
        rect(s, glow, lx + 3, ly + 2, lamp_w - 6, 3)


def draw_gt(body, w=124, h=70, lean=0, braking=False):
    """Big front-engined grand tourer: upright tail, wide shoulders."""
    s = surf(w, h)
    cx = w / 2
    lo = lean * 3.0
    tilt = lean * 1.5
    dark, darker = shade(body, 0.6), shade(body, 0.38)
    light = shade(body, 1.22)
    glass = (36, 44, 66)
    ground = h - 3
    _wheels(s, w, h, cx, ground, tilt, span=0.45, size=(24, 22))
    rect(s, (0, 0, 0, 120), cx - w * 0.42, ground - 2, w * 0.84, 4)

    poly(s, body, [(cx - w * 0.47, ground - 6 + tilt),
                   (cx + w * 0.47, ground - 6 - tilt),
                   (cx + w * 0.44, ground - 36 - tilt),
                   (cx - w * 0.44, ground - 36 + tilt)])
    poly(s, light, [(cx - w * 0.44, ground - 36 + tilt),
                    (cx + w * 0.44, ground - 36 - tilt),
                    (cx + w * 0.42, ground - 31 - tilt),
                    (cx - w * 0.42, ground - 31 + tilt)])
    poly(s, darker, [(cx - w * 0.45, ground - 6 + tilt),
                     (cx + w * 0.45, ground - 6 - tilt),
                     (cx + w * 0.41, ground - 14 - tilt),
                     (cx - w * 0.41, ground - 14 + tilt)])
    cab_top = ground - 56
    poly(s, dark, [(cx - w * 0.34 + lo, ground - 36 + tilt),
                   (cx + w * 0.34 + lo, ground - 36 - tilt),
                   (cx + w * 0.29 + lo, cab_top - tilt),
                   (cx - w * 0.29 + lo, cab_top + tilt)])
    poly(s, glass, [(cx - w * 0.30 + lo, ground - 38 + tilt),
                    (cx + w * 0.30 + lo, ground - 38 - tilt),
                    (cx + w * 0.25 + lo, cab_top + 4 - tilt),
                    (cx - w * 0.25 + lo, cab_top + 4 + tilt)])
    poly(s, shade(glass, 1.8), [(cx - w * 0.25 + lo, cab_top + 4 + tilt),
                                (cx - w * 0.02 + lo, cab_top + 4 - tilt),
                                (cx - w * 0.14 + lo, ground - 38),
                                (cx - w * 0.30 + lo, ground - 38 + tilt)])
    # quad round lamps
    for side in (-1, 1):
        for k in (0, 1):
            lx = cx + side * (w * 0.20 + k * w * 0.11)
            pygame.draw.circle(s, (170, 40, 30), (int(lx), int(ground - 24)), 7)
            col = (255, 80, 60) if not braking else (255, 210, 170)
            pygame.draw.circle(s, col, (int(lx), int(ground - 24)), 5)
    rect(s, (222, 222, 210), cx - 10, ground - 14, 20, 7)
    rect(s, (40, 40, 44), cx - 8, ground - 12, 16, 3)
    return s


def draw_coupe(body, w=104, h=62, lean=0, braking=False):
    """Small light hatch: short, upright, cheerful."""
    s = surf(w, h)
    cx = w / 2
    lo = lean * 2.6
    tilt = lean * 1.8
    dark, darker = shade(body, 0.6), shade(body, 0.4)
    light = shade(body, 1.25)
    glass = (40, 48, 70)
    ground = h - 3
    _wheels(s, w, h, cx, ground, tilt, span=0.42, size=(20, 19))
    rect(s, (0, 0, 0, 120), cx - w * 0.40, ground - 2, w * 0.80, 4)

    poly(s, body, [(cx - w * 0.44, ground - 5 + tilt),
                   (cx + w * 0.44, ground - 5 - tilt),
                   (cx + w * 0.41, ground - 26 - tilt),
                   (cx - w * 0.41, ground - 26 + tilt)])
    poly(s, darker, [(cx - w * 0.42, ground - 5 + tilt),
                     (cx + w * 0.42, ground - 5 - tilt),
                     (cx + w * 0.38, ground - 12 - tilt),
                     (cx - w * 0.38, ground - 12 + tilt)])
    cab_top = ground - 50
    poly(s, dark, [(cx - w * 0.38 + lo, ground - 26 + tilt),
                   (cx + w * 0.38 + lo, ground - 26 - tilt),
                   (cx + w * 0.34 + lo, cab_top - tilt),
                   (cx - w * 0.34 + lo, cab_top + tilt)])
    poly(s, glass, [(cx - w * 0.33 + lo, ground - 28 + tilt),
                    (cx + w * 0.33 + lo, ground - 28 - tilt),
                    (cx + w * 0.29 + lo, cab_top + 4 - tilt),
                    (cx - w * 0.29 + lo, cab_top + 4 + tilt)])
    poly(s, light, [(cx - w * 0.41, ground - 26 + tilt),
                    (cx + w * 0.41, ground - 26 - tilt),
                    (cx + w * 0.40, ground - 23 - tilt),
                    (cx - w * 0.40, ground - 23 + tilt)])
    _lamps(s, cx, ground - 22, w * 0.30, 18, braking, tilt)
    rect(s, (222, 222, 210), cx - 8, ground - 12, 16, 6)
    return s


def draw_van(body, w=112, h=86, lean=0, braking=False, ambulance=False):
    """Tall boxy people carrier - and, with the light bar, an ambulance."""
    s = surf(w, h)
    cx = w / 2
    lo = lean * 2.2
    tilt = lean * 2.4
    if ambulance:
        body = (242, 244, 248)
    dark, darker = shade(body, 0.62), shade(body, 0.42)
    glass = (42, 50, 72)
    ground = h - 3
    _wheels(s, w, h, cx, ground, tilt, span=0.43, size=(22, 20))
    rect(s, (0, 0, 0, 120), cx - w * 0.40, ground - 2, w * 0.80, 4)

    roof = ground - 68
    poly(s, body, [(cx - w * 0.45, ground - 5 + tilt),
                   (cx + w * 0.45, ground - 5 - tilt),
                   (cx + w * 0.43, roof - tilt),
                   (cx - w * 0.43, roof + tilt)])
    poly(s, shade(body, 1.12), [(cx - w * 0.43, roof + tilt),
                                (cx + w * 0.43, roof - tilt),
                                (cx + w * 0.42, roof + 4 - tilt),
                                (cx - w * 0.42, roof + 4 + tilt)])
    # rear doors: split line and windows
    poly(s, glass, [(cx - w * 0.36 + lo, roof + 8 + tilt),
                    (cx + w * 0.36 + lo, roof + 8 - tilt),
                    (cx + w * 0.36 + lo, roof + 30 - tilt),
                    (cx - w * 0.36 + lo, roof + 30 + tilt)])
    poly(s, shade(glass, 1.7), [(cx - w * 0.36 + lo, roof + 8 + tilt),
                                (cx - w * 0.06 + lo, roof + 8 - tilt),
                                (cx - w * 0.18 + lo, roof + 30),
                                (cx - w * 0.36 + lo, roof + 30 + tilt)])
    rect(s, darker, cx - 1, roof + 6, 2, ground - roof - 12)
    rect(s, darker, cx - w * 0.44, ground - 16, w * 0.88, 2)
    if ambulance:
        rect(s, (214, 40, 44), cx - w * 0.45, ground - 30, w * 0.90, 7)
        # red cross on the doors
        rect(s, (214, 40, 44), cx - 4, roof + 34, 8, 22)
        rect(s, (214, 40, 44), cx - 11, roof + 41, 22, 8)
        # roof light bar
        rect(s, (60, 62, 74), cx - w * 0.30, roof - 8, w * 0.60, 8)
        for i, col in enumerate([(70, 130, 255), (255, 70, 70)] * 2):
            rect(s, col, cx - w * 0.28 + i * w * 0.14, roof - 7, w * 0.12, 6)
    else:
        rect(s, shade(body, 0.8), cx - w * 0.44, ground - 30, w * 0.88, 3)
        # roof rails
        for side in (-1, 1):
            rect(s, darker, cx + side * w * 0.34 - 2, roof - 4, 4, 5)
    poly(s, darker, [(cx - w * 0.45, ground - 5 + tilt),
                     (cx + w * 0.45, ground - 5 - tilt),
                     (cx + w * 0.42, ground - 12 - tilt),
                     (cx - w * 0.42, ground - 12 + tilt)])
    # tall corner lamps
    lamp = (255, 70, 50) if not braking else (255, 210, 170)
    for side in (-1, 1):
        lx = cx + side * w * 0.38 - 7
        rect(s, shade(lamp, 0.5), lx, ground - 28, 14, 16)
        rect(s, lamp, lx + 1, ground - 27, 12, 14)
        rect(s, (255, 190, 90), lx + 2, ground - 26, 10, 4)
    rect(s, (222, 222, 210), cx - 10, ground - 12, 20, 7)
    return s


def draw_oncoming(body, w=112, h=64, lean=0, truck=False):
    """Front view, for traffic coming the other way: headlights, grille and a
    windscreen instead of tail lights and a rear deck."""
    s = surf(w, h)
    cx = w / 2
    lo = lean * 2.4
    tilt = lean * 1.4
    dark, darker = shade(body, 0.6), shade(body, 0.38)
    light = shade(body, 1.22)
    glass = (58, 74, 104)
    ground = h - 3

    if truck:
        _wheels(s, w, h, cx, ground, tilt, span=0.42, size=(22, 20))
        rect(s, (0, 0, 0, 120), cx - w * 0.42, ground - 2, w * 0.84, 4)
        roof = ground - 52
        poly(s, body, [(cx - w * 0.45, ground - 5 + tilt),
                       (cx + w * 0.45, ground - 5 - tilt),
                       (cx + w * 0.43, roof - tilt),
                       (cx - w * 0.43, roof + tilt)])
        poly(s, glass, [(cx - w * 0.37 + lo, roof + 5 + tilt),
                        (cx + w * 0.37 + lo, roof + 5 - tilt),
                        (cx + w * 0.37 + lo, roof + 24 - tilt),
                        (cx - w * 0.37 + lo, roof + 24 + tilt)])
        poly(s, shade(glass, 1.5), [(cx - w * 0.37 + lo, roof + 5 + tilt),
                                    (cx - w * 0.05 + lo, roof + 5 - tilt),
                                    (cx - w * 0.20 + lo, roof + 24),
                                    (cx - w * 0.37 + lo, roof + 24 + tilt)])
        rect(s, darker, cx - w * 0.45, ground - 20, w * 0.90, 8)
        rect(s, (190, 194, 205), cx - w * 0.30, ground - 18, w * 0.60, 4)
        lamp_y = ground - 16
        lamp_w = 16
    else:
        _wheels(s, w, h, cx, ground, tilt, span=0.44, size=(22, 20))
        rect(s, (0, 0, 0, 120), cx - w * 0.42, ground - 2, w * 0.84, 4)
        poly(s, body, [(cx - w * 0.46, ground - 5 + tilt),
                       (cx + w * 0.46, ground - 5 - tilt),
                       (cx + w * 0.43, ground - 30 - tilt),
                       (cx - w * 0.43, ground - 30 + tilt)])
        poly(s, light, [(cx - w * 0.43, ground - 30 + tilt),
                        (cx + w * 0.43, ground - 30 - tilt),
                        (cx + w * 0.41, ground - 26 - tilt),
                        (cx - w * 0.41, ground - 26 + tilt)])
        cab_top = ground - 48
        poly(s, dark, [(cx - w * 0.33 + lo, ground - 30 + tilt),
                       (cx + w * 0.33 + lo, ground - 30 - tilt),
                       (cx + w * 0.27 + lo, cab_top - tilt),
                       (cx - w * 0.27 + lo, cab_top + tilt)])
        poly(s, glass, [(cx - w * 0.29 + lo, ground - 32 + tilt),
                        (cx + w * 0.29 + lo, ground - 32 - tilt),
                        (cx + w * 0.23 + lo, cab_top + 3 - tilt),
                        (cx - w * 0.23 + lo, cab_top + 3 + tilt)])
        poly(s, shade(glass, 1.45),
             [(cx - w * 0.23 + lo, cab_top + 3 + tilt),
              (cx + w * 0.02 + lo, cab_top + 3 - tilt),
              (cx - w * 0.12 + lo, ground - 32),
              (cx - w * 0.29 + lo, ground - 32 + tilt)])
        rect(s, darker, cx - w * 0.44, ground - 14, w * 0.88, 7)
        lamp_y = ground - 26
        lamp_w = 20

    # headlights, with a little glow so they read at distance
    for side in (-1, 1):
        lx = cx + side * w * 0.29 - lamp_w / 2
        rect(s, (120, 118, 96), lx - 1, lamp_y - 1, lamp_w + 2, 11)
        rect(s, (255, 246, 198), lx, lamp_y, lamp_w, 9)
        rect(s, (255, 255, 255), lx + 2, lamp_y + 2, lamp_w - 4, 4)
    # indicators
    for side in (-1, 1):
        rect(s, (250, 168, 40), cx + side * w * 0.42 - 5, ground - 22, 8, 6)
    rect(s, (222, 222, 210), cx - 9, ground - 12, 18, 6)
    return s


def draw_police(body, w=124, h=72, lean=0, braking=False):
    """Interceptor saloon: two-tone with a roof light bar."""
    s = draw_gt((236, 238, 244), w=w, h=h, lean=lean, braking=braking)
    cx = w / 2
    lo = lean * 3.0
    ground = h - 3
    # dark lower flanks
    rect(s, (26, 28, 38), cx - w * 0.47, ground - 20, w * 0.94, 8)
    rect(s, (26, 28, 38), cx - w * 0.47, ground - 6, w * 0.20, 5)
    rect(s, (26, 28, 38), cx + w * 0.27, ground - 6, w * 0.20, 5)
    # light bar
    bar_y = ground - 62
    rect(s, (48, 50, 62), cx - w * 0.26 + lo, bar_y, w * 0.52, 8)
    for i, col in enumerate([(70, 130, 255), (255, 70, 70)] * 2):
        rect(s, col, cx - w * 0.24 + lo + i * w * 0.12, bar_y + 1,
             w * 0.10, 6)
    rect(s, (200, 204, 214), cx - w * 0.10, ground - 16, w * 0.20, 5)
    return s


def draw_f1(body, w=132, h=64, lean=0, braking=False):
    """Open-wheel single seater: exposed tyres, big rear wing, airbox."""
    s = surf(w, h)
    cx = w / 2
    lo = lean * 2.2
    tilt = lean * 1.2
    dark, darker = shade(body, 0.6), shade(body, 0.36)
    ground = h - 3

    # rear tyres, wide and proud of the body
    for side in (-1, 1):
        wx = cx + side * w * 0.36 - 15
        wy = ground - 28 + side * tilt * 0.5
        pygame.draw.ellipse(s, (24, 24, 30), (wx, wy, 30, 12))
        rect(s, (24, 24, 30), wx, wy + 6, 30, 22)
        rect(s, (46, 46, 56), wx + 2, wy + 7, 26, 3)
        rect(s, (140, 142, 156), wx + 9, wy + 14, 12, 11)
        rect(s, (84, 86, 98), wx + 9, wy + 20, 12, 5)
    rect(s, (0, 0, 0, 120), cx - w * 0.42, ground - 2, w * 0.84, 4)

    # sidepods and the body pod between the wheels
    for side in (-1, 1):
        poly(s, shade(body, 0.9),
             [(cx + side * w * 0.14, ground - 10 + tilt),
              (cx + side * w * 0.26, ground - 10 + tilt),
              (cx + side * w * 0.24, ground - 24),
              (cx + side * w * 0.13, ground - 26)])
    poly(s, body, [(cx - w * 0.16, ground - 6 + tilt),
                   (cx + w * 0.16, ground - 6 - tilt),
                   (cx + w * 0.13, ground - 30 - tilt),
                   (cx - w * 0.13, ground - 30 + tilt)])
    rect(s, darker, cx - w * 0.16, ground - 12, w * 0.32, 7)
    for i in range(5):
        rect(s, (18, 18, 24), cx - w * 0.14 + i * w * 0.06, ground - 11,
             w * 0.02, 5)
    # engine cover and airbox over the driver
    poly(s, dark, [(cx - w * 0.10 + lo, ground - 30 + tilt),
                   (cx + w * 0.10 + lo, ground - 30 - tilt),
                   (cx + w * 0.06 + lo, ground - 46),
                   (cx - w * 0.06 + lo, ground - 46)])
    rect(s, (30, 32, 44), cx - w * 0.05 + lo, ground - 52, w * 0.10, 8)
    pygame.draw.circle(s, (240, 200, 60),
                       (int(cx + lo), int(ground - 48)), 5)
    # rear wing on end plates
    wing_y = ground - 58
    poly(s, shade(body, 0.85), [(cx - w * 0.40, wing_y + 7 + tilt),
                                (cx + w * 0.40, wing_y + 7 - tilt),
                                (cx + w * 0.40, wing_y - tilt),
                                (cx - w * 0.40, wing_y + tilt)])
    poly(s, shade(body, 1.25), [(cx - w * 0.40, wing_y + 2 + tilt),
                                (cx + w * 0.40, wing_y + 2 - tilt),
                                (cx + w * 0.40, wing_y - tilt),
                                (cx - w * 0.40, wing_y + tilt)])
    for side in (-1, 1):
        rect(s, darker, cx + side * w * 0.40 - 3, wing_y - 2, 5, 14)
    lamp = (255, 70, 50) if not braking else (255, 220, 190)
    rect(s, lamp, cx - 5, ground - 26, 10, 7)
    return s


def draw_bike(body, w=68, h=78, lean=0, braking=False):
    """Motorcycle and rider from behind - narrow enough to change the game."""
    s = surf(w, h)
    cx = w / 2
    tilt = lean * 4.5            # bikes lean properly
    lo = lean * 3.0
    ground = h - 3
    dark, light = shade(body, 0.55), shade(body, 1.2)

    rect(s, (0, 0, 0, 120), cx - 11, ground - 2, 22, 4)
    # rear tyre and swingarm
    rect(s, (22, 22, 28), cx - 8 + tilt * 0.4, ground - 26, 16, 26)
    rect(s, (48, 48, 58), cx - 6 + tilt * 0.4, ground - 22, 12, 4)
    rect(s, (150, 152, 165), cx - 3 + tilt * 0.4, ground - 16, 6, 8)
    for side in (-1, 1):
        rect(s, (70, 72, 84), cx + side * 11 + tilt * 0.4 - 2, ground - 20,
             4, 12)
    # exhaust cans
    for side in (-1, 1):
        rect(s, (168, 170, 182), cx + side * 15 + tilt * 0.5 - 4,
             ground - 24, 8, 9)
        rect(s, (96, 98, 110), cx + side * 15 + tilt * 0.5 - 3,
             ground - 22, 6, 4)
    # tail unit and seat
    poly(s, body, [(cx - 11 + tilt, ground - 24), (cx + 11 + tilt, ground - 24),
                   (cx + 8 + lo, ground - 42), (cx - 8 + lo, ground - 42)])
    poly(s, light, [(cx - 10 + tilt, ground - 30), (cx + 10 + tilt, ground - 30),
                    (cx + 9 + tilt, ground - 26), (cx - 9 + tilt, ground - 26)])
    lamp = (255, 70, 50) if not braking else (255, 220, 190)
    rect(s, shade(lamp, 0.5), cx - 7 + tilt, ground - 36, 14, 8)
    rect(s, lamp, cx - 6 + tilt, ground - 35, 12, 6)
    poly(s, dark, [(cx - 8 + lo, ground - 42), (cx + 8 + lo, ground - 42),
                   (cx + 7 + lo, ground - 48), (cx - 7 + lo, ground - 48)])
    # rider: hunched back, elbows out, helmet
    poly(s, (40, 44, 64), [(cx - 10 + lo, ground - 44),
                           (cx + 10 + lo, ground - 44),
                           (cx + 9 + lo, ground - 60),
                           (cx - 9 + lo, ground - 60)])
    rect(s, body, cx - 10 + lo, ground - 52, 20, 4)
    poly(s, (54, 60, 84), [(cx - 9 + lo, ground - 60),
                           (cx + 9 + lo, ground - 60),
                           (cx + 7 + lo, ground - 65),
                           (cx - 7 + lo, ground - 65)])
    for side in (-1, 1):
        rect(s, (40, 44, 64), cx + side * 11 + lo - 3, ground - 58, 6, 11)
        rect(s, (24, 26, 38), cx + side * 12 + lo - 3, ground - 50, 6, 5)
    pygame.draw.circle(s, (232, 234, 242), (int(cx + lo), int(ground - 70)), 8)
    pygame.draw.circle(s, (36, 42, 62), (int(cx + lo), int(ground - 72)), 6)
    rect(s, body, cx - 7 + lo, ground - 77, 14, 5)
    return s


def gen_cars():
    """Ten frames per playable car (five steering angles x brake lights) plus
    the rival field."""
    names = []
    builders = {
        'wedge': lambda **kw: draw_car((214, 32, 40), **kw),
        'gt': lambda **kw: draw_gt((36, 78, 196), **kw),
        'coupe': lambda **kw: draw_coupe((248, 196, 32), **kw),
        'ambulance': lambda **kw: draw_van(None, ambulance=True, **kw),
        'van': lambda **kw: draw_van((72, 148, 108), **kw),
        'police': lambda **kw: draw_police(None, **kw),
        'f1': lambda **kw: draw_f1((28, 34, 58), **kw),
        'bike': lambda **kw: draw_bike((228, 96, 32), **kw),
    }
    for key, build in builders.items():
        for lean in (-2, -1, 0, 1, 2):
            for braking in (False, True):
                tag = 'b' if braking else 'n'
                # the taller bodies lean harder but steer through fewer angles
                amount = lean if key in ('wedge', 'gt', 'coupe', 'police',
                                         'f1', 'bike') else \
                    max(-1, min(1, lean))
                img = build(lean=amount, braking=braking)
                names.append(save(img, 'car_%s_%d%s' % (key, lean + 2, tag)))

    rivals = [(240, 190, 40), (40, 120, 220), (240, 240, 245),
              (30, 170, 90), (170, 60, 200), (250, 120, 30)]
    for i, col in enumerate(rivals):
        for lean in (-1, 0, 1):
            img = draw_car(col, w=110, h=62, lean=lean, detail=(i % 2 == 0))
            names.append(save(img, 'car_rival%d_%d' % (i, lean + 1)))

    # traffic coming the other way, seen head on
    oncoming = [(214, 214, 220), (56, 92, 168), (176, 52, 48),
                (208, 176, 64), (72, 132, 96), (120, 120, 132)]
    for i, col in enumerate(oncoming):
        for lean in (-1, 0, 1):
            img = draw_oncoming(col, lean=lean)
            names.append(save(img, 'car_onc%d_%d' % (i, lean + 1)))
    for i, col in enumerate([(226, 226, 230), (196, 140, 60)]):
        for lean in (-1, 0, 1):
            img = draw_oncoming(col, w=118, h=76, lean=lean, truck=True)
            names.append(save(img, 'car_truck%d_%d' % (i, lean + 1)))
    return names


# --------------------------------------------------------------------------
# Scenery
# --------------------------------------------------------------------------

def tree(w, h, trunk_col, leaf, dark_leaf, blobs, rng):
    s = surf(w, h)
    tw = max(3, w // 8)
    rect(s, trunk_col, w / 2 - tw / 2, h * 0.62, tw, h * 0.38)
    rect(s, shade(trunk_col, 0.6), w / 2 - tw / 2, h * 0.62, tw / 2, h * 0.38)
    for i in range(blobs):
        r = rng.uniform(0.20, 0.30) * w
        bx = w / 2 + rng.uniform(-0.22, 0.22) * w
        by = h * 0.36 + rng.uniform(-0.24, 0.16) * h
        pygame.draw.circle(s, dark_leaf, (int(bx), int(by)), int(r))
        pygame.draw.circle(s, leaf, (int(bx - r * 0.25), int(by - r * 0.28)),
                           int(r * 0.72))
    return s


def pine(w, h, needle, dark, snow=False):
    s = surf(w, h)
    rect(s, (74, 52, 34), w / 2 - w * 0.06, h * 0.80, w * 0.12, h * 0.20)
    tiers = 4
    for i in range(tiers):
        t = i / tiers
        top = h * (0.05 + 0.19 * i)
        bot = h * (0.34 + 0.175 * i)
        half = w * (0.16 + 0.34 * t) / 1.0
        poly(s, dark, [(w / 2, top), (w / 2 + half, bot), (w / 2 - half, bot)])
        poly(s, needle, [(w / 2, top), (w / 2 + half * 0.55, bot),
                         (w / 2 - half, bot)])
        if snow:
            poly(s, (238, 244, 252), [
                (w / 2, top), (w / 2 + half * 0.42, bot * 0.62 + top * 0.38),
                (w / 2 - half * 0.42, bot * 0.62 + top * 0.38)])
    return s


def rock(w, h, base, rng, snowy=False):
    s = surf(w, h)
    pts = []
    n = 7
    for i in range(n):
        a = math.pi + math.pi * i / (n - 1)
        r = rng.uniform(0.72, 1.0)
        pts.append((w / 2 + math.cos(a) * w / 2 * r,
                    h - abs(math.sin(a)) * h * r))
    pts.append((w, h))
    pts.append((0, h))
    poly(s, shade(base, 0.7), pts)
    poly(s, base, [(p[0] * 0.82 + w * 0.09, p[1] * 0.86 + h * 0.14)
                   for p in pts])
    poly(s, shade(base, 1.3), [(w * 0.3, h * 0.42), (w * 0.55, h * 0.22),
                               (w * 0.62, h * 0.55), (w * 0.36, h * 0.62)])
    if snowy:
        poly(s, (240, 246, 255), [(w * 0.22, h * 0.5), (w * 0.5, h * 0.16),
                                  (w * 0.78, h * 0.48), (w * 0.6, h * 0.4),
                                  (w * 0.46, h * 0.5), (w * 0.34, h * 0.42)])
    return s


def cactus(w, h, arms):
    s = surf(w, h)
    g, gd, gl = (58, 132, 62), (36, 92, 44), (96, 172, 92)
    bw = w * 0.26
    rect(s, gd, w / 2 - bw / 2, h * 0.10, bw, h * 0.90)
    rect(s, g, w / 2 - bw / 2 + 2, h * 0.10, bw - 4, h * 0.90)
    rect(s, gl, w / 2 - bw / 2 + 2, h * 0.10, 2, h * 0.90)
    pygame.draw.circle(s, g, (int(w / 2), int(h * 0.12)), int(bw / 2))
    for i, (side, ay) in enumerate(arms):
        aw = w * 0.20
        x0 = w / 2 + side * bw / 2
        x1 = w / 2 + side * w * 0.42
        rect(s, gd, min(x0, x1), h * ay, abs(x1 - x0), aw * 0.8)
        rect(s, g, min(x0, x1), h * ay + 1, abs(x1 - x0), aw * 0.8 - 2)
        rect(s, gd, x1 - (aw / 2 if side > 0 else -aw / 2) - aw / 2,
             h * (ay - 0.26), aw, h * 0.30)
        rect(s, g, x1 - (aw / 2 if side > 0 else -aw / 2) - aw / 2 + 1,
             h * (ay - 0.26), aw - 2, h * 0.30)
    return s


def building(w, h, wall, rng, lit_chance=0.45, night=True):
    s = surf(w, h)
    rect(s, shade(wall, 0.62), 0, 0, w, h)
    rect(s, wall, 0, 0, w * 0.78, h)
    rect(s, shade(wall, 1.2), 0, 0, w * 0.06, h)
    rect(s, shade(wall, 0.45), 0, 0, w, max(3, h * 0.03))
    win = max(3, int(w * 0.11))
    gap = max(2, int(w * 0.08))
    cols = max(1, int((w - gap) // (win + gap)))
    rows = max(1, int((h - gap * 3) // (win + gap + 2)))
    ox = (w - (cols * (win + gap) - gap)) / 2
    for r in range(rows):
        for c in range(cols):
            x = ox + c * (win + gap)
            y = gap * 2 + r * (win + gap + 2)
            if y + win > h - gap:
                continue
            if night and rng.random() < lit_chance:
                col = rng.choice([(255, 226, 140), (255, 196, 96),
                                  (200, 226, 255)])
            else:
                col = (38, 44, 62) if night else (120, 148, 176)
            rect(s, col, x, y, win, win)
    # ground floor entrance
    rect(s, (30, 34, 48), w * 0.36, h - h * 0.09, w * 0.28, h * 0.09)
    return s


def gen_scenery():
    rng = random.Random(1988)
    names = []

    # --- countryside -----------------------------------------------------
    names.append(save(tree(90, 110, (92, 64, 40), (86, 176, 66),
                           (52, 122, 44), 5, rng), 'obj_tree_oak'))
    names.append(save(tree(70, 80, (96, 70, 44), (120, 196, 82),
                           (66, 140, 52), 4, rng), 'obj_tree_round'))
    names.append(save(tree(54, 46, (80, 60, 40), (110, 178, 76),
                           (60, 126, 50), 4, rng), 'obj_bush'))

    hay = surf(60, 46)
    for i in range(6):
        c = mix((214, 178, 92), (150, 116, 54), i / 5)
        pygame.draw.ellipse(hay, c, (i, 2 + i, 60 - 2 * i, 42 - 2 * i))
    names.append(save(hay, 'obj_haybale'))

    barn = surf(150, 116)
    rect(barn, (168, 46, 40), 8, 42, 134, 74)
    rect(barn, (140, 34, 30), 8, 42, 134, 6)
    poly(barn, (198, 62, 52), [(2, 46), (75, 4), (148, 46)])
    poly(barn, (150, 40, 34), [(75, 4), (148, 46), (128, 46), (75, 16)])
    rect(barn, (238, 236, 226), 60, 70, 30, 46)
    rect(barn, (60, 46, 40), 64, 74, 22, 42)
    rect(barn, (238, 236, 226), 20, 58, 18, 18)
    rect(barn, (238, 236, 226), 112, 58, 18, 18)
    names.append(save(barn, 'obj_barn'))

    fence = surf(80, 40)
    rect(fence, (206, 200, 184), 4, 6, 6, 34)
    rect(fence, (206, 200, 184), 70, 6, 6, 34)
    rect(fence, (226, 220, 206), 0, 12, 80, 5)
    rect(fence, (226, 220, 206), 0, 24, 80, 5)
    names.append(save(fence, 'obj_fence'))

    # --- desert ----------------------------------------------------------
    names.append(save(cactus(86, 120, [(1, 0.52), (-1, 0.66)]),
                      'obj_cactus_big'))
    names.append(save(cactus(60, 84, [(-1, 0.58)]), 'obj_cactus_small'))
    names.append(save(rock(96, 62, (186, 142, 92), rng), 'obj_rock_sand'))
    names.append(save(rock(64, 40, (166, 124, 80), rng), 'obj_rock_small'))

    palm = surf(90, 130)
    for i in range(9):
        rect(palm, (120, 92, 58), 42 + math.sin(i * 0.5) * 3, 130 - i * 10, 9, 11)
    for a in range(7):
        ang = math.pi + a * math.pi / 6
        ex = 46 + math.cos(ang) * 40
        ey = 40 + math.sin(ang) * 26
        poly(palm, (44, 112, 52), [(46, 42), (ex, ey), (ex * 0.6 + 46 * 0.4,
                                                        ey + 12)])
        poly(palm, (70, 152, 68), [(46, 40), (ex, ey - 2),
                                   (ex * 0.7 + 46 * 0.3, ey + 5)])
    names.append(save(palm, 'obj_palm'))

    skull = surf(46, 36)
    pygame.draw.ellipse(skull, (232, 226, 206), (6, 2, 34, 26))
    rect(skull, (232, 226, 206), 14, 22, 18, 12)
    rect(skull, (60, 54, 48), 12, 12, 8, 8)
    rect(skull, (60, 54, 48), 26, 12, 8, 8)
    for hx in (2, 36):
        pygame.draw.ellipse(skull, (222, 214, 194), (hx, 4, 10, 14))
    names.append(save(skull, 'obj_skull'))

    # --- mountains / winter ----------------------------------------------
    names.append(save(pine(80, 130, (46, 120, 62), (28, 84, 46)),
                      'obj_pine'))
    names.append(save(pine(64, 100, (52, 130, 68), (32, 92, 50)),
                      'obj_pine_small'))
    names.append(save(pine(80, 130, (58, 112, 78), (36, 78, 58), snow=True),
                      'obj_pine_snow'))
    names.append(save(pine(62, 98, (62, 118, 82), (38, 84, 60), snow=True),
                      'obj_pine_snow_small'))
    names.append(save(rock(110, 70, (128, 130, 140), rng), 'obj_rock_grey'))
    names.append(save(rock(110, 70, (150, 156, 170), rng, snowy=True),
                      'obj_rock_snow'))

    bank = surf(120, 44)
    poly(bank, (206, 216, 234), [(0, 44), (14, 16), (46, 6), (86, 12),
                                 (118, 40), (120, 44)])
    poly(bank, (246, 250, 255), [(10, 30), (26, 12), (60, 8), (86, 16),
                                 (100, 30), (60, 22)])
    names.append(save(bank, 'obj_snowbank'))

    chalet = surf(140, 110)
    rect(chalet, (122, 84, 52), 14, 48, 112, 62)
    for i in range(5):
        rect(chalet, (98, 66, 40), 14, 52 + i * 12, 112, 2)
    poly(chalet, (86, 60, 40), [(2, 54), (70, 8), (138, 54)])
    poly(chalet, (240, 246, 255), [(2, 54), (70, 8), (138, 54), (128, 54),
                                   (70, 18), (12, 54)])
    rect(chalet, (250, 226, 150), 34, 62, 22, 20)
    rect(chalet, (250, 226, 150), 84, 62, 22, 20)
    rect(chalet, (58, 42, 30), 60, 78, 22, 32)
    names.append(save(chalet, 'obj_chalet'))

    pole = surf(20, 90)
    rect(pole, (240, 244, 250), 6, 0, 8, 90)
    rect(pole, (220, 40, 40), 6, 0, 8, 16)
    names.append(save(pole, 'obj_snowpole'))

    # --- city ------------------------------------------------------------
    walls = [(72, 78, 108), (92, 84, 96), (64, 70, 96), (104, 92, 88),
             (58, 64, 88)]
    sizes = [(120, 260), (150, 200), (100, 320), (170, 150), (130, 230)]
    for i, ((w, h), col) in enumerate(zip(sizes, walls)):
        names.append(save(building(w, h, col, rng), 'obj_building%d' % i))

    lamp = surf(60, 150)
    rect(lamp, (58, 62, 76), 4, 10, 8, 140)
    rect(lamp, (58, 62, 76), 8, 10, 40, 7)
    poly(lamp, (70, 74, 90), [(40, 15), (58, 15), (54, 26), (44, 26)])
    poly(lamp, (255, 236, 170), [(42, 24), (56, 24), (58, 30), (40, 30)])
    names.append(save(lamp, 'obj_streetlamp'))

    cone = surf(30, 36)
    poly(cone, (238, 108, 26), [(15, 2), (26, 30), (4, 30)])
    rect(cone, (250, 250, 250), 8, 16, 14, 5)
    rect(cone, (200, 80, 16), 2, 30, 26, 6)
    names.append(save(cone, 'obj_cone'))

    for i, (word, bg, fg) in enumerate([('TURBO', (222, 40, 60), (255, 240, 120)),
                                        ('NITRO', (26, 60, 180), (255, 255, 255)),
                                        ('SPEED', (250, 200, 30), (40, 30, 90))]):
        b = surf(150, 110)
        rect(b, (70, 70, 80), 30, 60, 8, 50)
        rect(b, (70, 70, 80), 112, 60, 8, 50)
        rect(b, (40, 40, 48), 6, 6, 138, 62)
        rect(b, bg, 10, 10, 130, 54)
        pixelfont.draw_text(b, word, 75, 26, fg, scale=2, center=True)
        names.append(save(b, 'obj_billboard%d' % i))

    # --- shared ----------------------------------------------------------
    for tag, arrow in (('l', -1), ('r', 1)):
        sg = surf(70, 90)
        rect(sg, (150, 150, 158), 31, 34, 8, 56)
        rect(sg, (30, 30, 36), 2, 2, 66, 36)
        rect(sg, (250, 216, 40), 5, 5, 60, 30)
        for k in range(3):
            x0 = 12 + k * 16
            poly(sg, (30, 30, 36), [(x0, 10), (x0 + 12 * arrow, 20),
                                    (x0, 30), (x0 + 4 * arrow, 20)])
        names.append(save(sg, 'obj_sign_%s' % tag))

    tyre_wall = surf(70, 34)
    for i in range(3):
        for j in range(2):
            c = (220, 40, 40) if (i + j) % 2 == 0 else (240, 240, 240)
            pygame.draw.ellipse(tyre_wall, c, (i * 23, j * 15, 24, 18))
            pygame.draw.ellipse(tyre_wall, (40, 40, 46),
                                (i * 23 + 8, j * 15 + 6, 8, 6))
    names.append(save(tyre_wall, 'obj_tyrewall'))

    # start / finish gantry
    g = surf(420, 170)
    rect(g, (46, 50, 64), 6, 40, 26, 130)
    rect(g, (46, 50, 64), 388, 40, 26, 130)
    rect(g, (66, 70, 88), 6, 40, 8, 130)
    rect(g, (66, 70, 88), 388, 40, 8, 130)
    rect(g, (28, 30, 40), 0, 18, 420, 58)
    for i in range(28):
        for j in range(2):
            c = (245, 245, 245) if (i + j) % 2 == 0 else (24, 24, 28)
            rect(g, c, 4 + i * 15, 22 + j * 8, 15, 8)
    rect(g, (198, 36, 46), 4, 40, 412, 32)
    pixelfont.draw_text(g, 'START', 210, 46, (255, 240, 140), scale=4,
                        center=True, shadow=(90, 12, 20))
    names.append(save(g, 'obj_gantry'))

    return names


# --------------------------------------------------------------------------
# Parallax backdrops
# --------------------------------------------------------------------------

def sky_gradient(w, h, top, bottom, sun=None, stars=0, rng=None):
    s = surf(w, h)
    for y in range(h):
        rect(s, mix(top, bottom, (y / (h - 1)) ** 0.85), 0, y, w, 1)
    if stars and rng:
        for _ in range(stars):
            x = rng.randrange(w)
            y = rng.randrange(int(h * 0.55))
            b = rng.choice([(255, 255, 255), (200, 210, 255), (255, 240, 210)])
            rect(s, b, x, y, 1, 1)
    if sun:
        sx, sy, r, col, halo = sun
        # halo goes on its own layer: drawing translucent shapes straight onto
        # an SRCALPHA surface replaces pixels instead of blending them.
        glow = surf(w, h)
        for i in range(12, 0, -1):
            pygame.draw.circle(glow, halo + (int(10 + 4 * (12 - i)),),
                               (sx, sy), int(r * (1 + i * 0.20)),
                               max(1, int(r * 0.22)))
        s.blit(glow, (0, 0))
        pygame.draw.circle(s, col, (sx, sy), r)
        pygame.draw.circle(s, shade(col, 1.15), (sx, sy), int(r * 0.7))
    return s


def ridge(w, h, base_col, peaks, rng, snow=None, jag=1.0, seed_y=0.45):
    """A silhouette mountain/hill band, tileable at the seam."""
    s = surf(w, h)
    ys = []
    step = w / peaks
    for i in range(peaks + 1):
        ys.append(h * (seed_y + rng.uniform(-0.30, 0.30) * jag))
    ys[-1] = ys[0]
    pts = [(0, h)]
    for i in range(peaks + 1):
        x = i * step
        pts.append((x, ys[i]))
        if i < peaks:
            pts.append((x + step * 0.5,
                        (ys[i] + ys[i + 1]) / 2 + rng.uniform(0, 0.18) * h))
    pts.append((w, h))
    poly(s, base_col, pts)
    hi = shade(base_col, 1.25)
    for i in range(peaks):
        x = i * step
        poly(s, hi, [(x, ys[i]), (x + step * 0.5, (ys[i] + ys[i + 1]) / 2 + 6),
                     (x + step * 0.18, h)])
    if snow:
        for i in range(peaks + 1):
            x = i * step
            cap = h * 0.16
            poly(s, snow, [(x, ys[i]), (x + step * 0.22, ys[i] + cap),
                           (x + step * 0.1, ys[i] + cap * 0.6),
                           (x - step * 0.05, ys[i] + cap * 0.9),
                           (x - step * 0.2, ys[i] + cap)])
    return s


def skyline(w, h, rng):
    s = surf(w, h)
    x = 0
    while x < w:
        bw = rng.randrange(24, 60)
        bh = rng.randrange(int(h * 0.35), int(h * 0.95))
        col = rng.choice([(38, 40, 62), (46, 44, 68), (30, 34, 54)])
        rect(s, col, x, h - bh, bw, bh)
        rect(s, shade(col, 1.3), x, h - bh, 3, bh)
        if rng.random() < 0.35:
            rect(s, col, x + bw * 0.35, h - bh - 12, 5, 12)
            rect(s, (240, 70, 70), x + bw * 0.35, h - bh - 14, 5, 3)
        for wy in range(int(h - bh) + 5, h - 4, 7):
            for wx in range(int(x) + 4, int(x + bw) - 4, 7):
                if rng.random() < 0.42:
                    rect(s, rng.choice([(255, 224, 140), (255, 190, 90),
                                        (170, 210, 255)]), wx, wy, 3, 4)
        x += bw + rng.randrange(2, 10)
    return s


def treeline(w, h, rng, cols, snowy=False):
    s = surf(w, h)
    x = -10
    while x < w + 10:
        th = rng.randrange(int(h * 0.45), int(h * 1.0))
        tw = rng.randrange(14, 26)
        c = rng.choice(cols)
        poly(s, c, [(x + tw / 2, h - th), (x + tw, h), (x, h)])
        if snowy:
            poly(s, (232, 240, 252), [(x + tw / 2, h - th),
                                      (x + tw * 0.72, h - th * 0.45),
                                      (x + tw * 0.28, h - th * 0.45)])
        x += rng.randrange(9, 20)
    rect(s, cols[0], 0, h - 4, w, 4)
    return s


BG_W = 640
SKY_H = 120


def gen_backgrounds():
    names = []
    rng = random.Random(7)

    # City -- dusk turning to night
    s = sky_gradient(BG_W, SKY_H, (14, 12, 42), (238, 96, 76), stars=90, rng=rng,
                     sun=(470, 92, 20, (255, 210, 120), (255, 140, 90)))
    names.append(save(s, 'bg_city_sky'))
    names.append(save(skyline(BG_W, 70, rng), 'bg_city_far'))
    near = surf(BG_W, 46)
    rect(near, (26, 28, 44), 0, 20, BG_W, 26)
    x = 0
    while x < BG_W:
        bh = rng.randrange(14, 34)
        rect(near, (20, 22, 36), x, 46 - bh, rng.randrange(20, 44), bh)
        x += rng.randrange(24, 54)
    names.append(save(near, 'bg_city_near'))

    # Countryside -- bright blue day
    s = sky_gradient(BG_W, SKY_H, (52, 118, 220), (176, 216, 248))
    for _ in range(14):
        cx = rng.randrange(BG_W)
        cy = rng.randrange(14, 70)
        for k in range(rng.randrange(3, 6)):
            r = rng.randrange(8, 20)
            pygame.draw.circle(s, (255, 255, 255),
                               (cx + k * 12 - 12, cy + rng.randrange(-4, 5)), r)
            pygame.draw.circle(s, (218, 232, 250),
                               (cx + k * 12 - 12, cy + 5 + rng.randrange(0, 4)),
                               int(r * 0.7))
    names.append(save(s, 'bg_country_sky'))
    names.append(save(ridge(BG_W, 60, (96, 148, 96), 7, rng, jag=0.6,
                            seed_y=0.5), 'bg_country_far'))
    names.append(save(treeline(BG_W, 44, rng,
                               [(56, 116, 58), (44, 100, 50), (70, 136, 66)]),
                      'bg_country_near'))

    # Desert -- hazy heat
    s = sky_gradient(BG_W, SKY_H, (86, 150, 226), (250, 214, 158),
                     sun=(150, 76, 26, (255, 248, 210), (255, 220, 140)))
    names.append(save(s, 'bg_desert_sky'))
    mesa = surf(BG_W, 62)
    x = -20
    while x < BG_W + 20:
        mw = rng.randrange(60, 140)
        mh = rng.randrange(22, 52)
        col = rng.choice([(184, 118, 82), (166, 104, 74), (198, 136, 96)])
        poly(mesa, col, [(x, 62), (x + 8, 62 - mh), (x + mw - 8, 62 - mh),
                         (x + mw, 62)])
        poly(mesa, shade(col, 1.2), [(x, 62), (x + 8, 62 - mh),
                                     (x + mw * 0.35, 62 - mh), (x + mw * 0.2, 62)])
        x += mw + rng.randrange(-10, 40)
    names.append(save(mesa, 'bg_desert_far'))
    dunes = surf(BG_W, 40)
    for i in range(3):
        c = mix((228, 190, 132), (206, 162, 106), i / 2)
        pts = [(0, 40)]
        for x in range(0, BG_W + 20, 40):
            pts.append((x, 26 + i * 4 - math.sin(x * 0.02 + i) * 9))
        pts.append((BG_W, 40))
        poly(dunes, c, pts)
    names.append(save(dunes, 'bg_desert_near'))

    # Winter mountains -- cold and pale
    s = sky_gradient(BG_W, SKY_H, (96, 126, 176), (216, 226, 240))
    names.append(save(s, 'bg_winter_sky'))
    names.append(save(ridge(BG_W, 84, (118, 132, 162), 6, rng, jag=1.35,
                            snow=(246, 250, 255), seed_y=0.30),
                      'bg_winter_far'))
    names.append(save(treeline(BG_W, 46, rng,
                               [(52, 82, 76), (44, 72, 68), (62, 94, 84)],
                               snowy=True), 'bg_winter_near'))

    # Summer mountains -- deep alpine blue
    s = sky_gradient(BG_W, SKY_H, (24, 78, 190), (146, 200, 246))
    for _ in range(7):
        cx = rng.randrange(BG_W)
        cy = rng.randrange(10, 46)
        for k in range(4):
            pygame.draw.circle(s, (255, 255, 255), (cx + k * 14 - 14, cy),
                               rng.randrange(7, 15))
    names.append(save(s, 'bg_summer_sky'))
    names.append(save(ridge(BG_W, 80, (96, 116, 118), 5, rng, jag=1.2,
                            snow=(240, 248, 255), seed_y=0.26),
                      'bg_summer_far'))
    names.append(save(ridge(BG_W, 50, (62, 108, 74), 9, rng, jag=0.8,
                            seed_y=0.42), 'bg_summer_near'))
    return names


def gen_effects():
    names = []
    for i, r in enumerate((4, 7, 11)):
        s = surf(r * 2, r * 2)
        pygame.draw.circle(s, (255, 255, 255, 190), (r, r), r)
        pygame.draw.circle(s, (255, 255, 255, 90), (r, r), max(1, r - 2))
        names.append(save(s, 'fx_smoke%d' % i))
    s = surf(3, 3)
    s.fill((255, 255, 255, 235))
    names.append(save(s, 'fx_flake'))
    return names


def main():
    pygame.init()
    os.makedirs(OUT, exist_ok=True)
    n = []
    n += gen_cars()
    n += gen_scenery()
    n += gen_backgrounds()
    n += gen_effects()
    print('generated %d sprites -> %s' % (len(n), OUT))


if __name__ == '__main__':
    main()
