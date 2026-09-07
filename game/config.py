"""Render scale.

The game is designed on a 320x200 grid. `SCALE` multiplies the internal
render resolution: 1 is the original chunky look, 3 renders the world at
960x600 while the HUD and menus stay on the 320x200 grid and are scaled up
as a whole, so the pixel font stays perfectly crisp.

It is read once at import time from the environment, because render.py turns
it into module constants that everything else imports by name. main.py sets
the variable from its command line before importing anything else.
"""

import os

BASE_WIDTH, BASE_HEIGHT = 320, 200
MAX_SCALE = 4


def _read_scale():
    raw = os.environ.get('LATE_APEX_SCALE', '1')
    try:
        n = int(raw)
    except ValueError:
        return 1
    return max(1, min(MAX_SCALE, n))


SCALE = _read_scale()
HIRES = SCALE > 1
