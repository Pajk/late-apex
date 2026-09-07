"""The optional hi-res mode.

The render scale is read once at import time, so it cannot be flipped inside a
running process - these checks run the game in a subprocess with the
environment variable set, exactly as `--hires` does.
"""

import json
import os
import subprocess
import sys

from tests import harness

PROBE = r'''
import os, sys, tempfile, json, random
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['LATE_APEX_DATA_DIR'] = tempfile.mkdtemp()
sys.path.insert(0, %(root)r)
import pygame
from game.config import SCALE, BASE_WIDTH, BASE_HEIGHT
from game.render import WIDTH, HEIGHT
from game.app import App
from game.race import Race, MAX_SPEED
pygame.init()
app = App(%(root)r)
def press(k):
    app.on_key(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))
def step(n):
    for _ in range(n):
        app.update(1 / 60.0); app.draw(); app.present()
step(40)
title_colours = len({app.screen.get_at((x, y))[:3]
                     for x in range(8, WIDTH, 29) for y in range(8, HEIGHT, 19)})
for _ in range(3):
    press(pygame.K_RETURN); step(50)
racing = app.state
r = app.race
r.state = Race.STATE_RACING
r.player.speed = MAX_SPEED * 0.7
for _ in range(240):
    app.update(1 / 60.0)
app.draw(); app.present()
race_colours = len({app.screen.get_at((x, y))[:3]
                    for x in range(8, WIDTH, 29) for y in range(8, HEIGHT, 19)})
# the HUD must have drawn onto the low-res layer, not the world surface
ui_used = any(app.ui.get_at((x, y))[3] for x in range(0, BASE_WIDTH, 7)
              for y in range(0, 26))
print('RESULT' + json.dumps({
    'scale': SCALE, 'world': [WIDTH, HEIGHT], 'ui': list(app.ui.get_size()),
    'window': list(app.window.get_size()), 'separate_ui': app.ui is not app.screen,
    'title_colours': title_colours, 'race_colours': race_colours,
    'ui_used': bool(ui_used), 'car_w': r.car['width'] * SCALE,
}))
'''


def _probe(scale):
    env = dict(os.environ)
    env['LATE_APEX_SCALE'] = str(scale)
    env.pop('LATE_APEX_DATA_DIR', None)
    out = subprocess.run(
        [sys.executable, '-c', PROBE % {'root': harness.ROOT}],
        capture_output=True, text=True, env=env, timeout=180)
    for line in out.stdout.splitlines():
        if line.startswith('RESULT'):
            return json.loads(line[6:])
    raise AssertionError('probe failed at scale %s:\n%s\n%s'
                         % (scale, out.stdout[-2000:], out.stderr[-2000:]))


def run():
    c = harness.Checks('hi-res')

    base = _probe(1)
    c.check(base['scale'] == 1, 'scale 1 is not the default behaviour')
    c.check(base['world'] == [320, 200],
            'scale 1 no longer renders at 320x200 (got %s)' % base['world'])
    c.check(not base['separate_ui'],
            'scale 1 should draw the HUD straight onto the world surface')
    c.check(base['window'] == [960, 600],
            'window is not 960x600 at scale 1 (got %s)' % base['window'])

    hi = _probe(3)
    c.check(hi['world'] == [960, 600],
            'hi-res does not render at 960x600 (got %s)' % hi['world'])
    c.check(hi['ui'] == [320, 200],
            'the HUD layer left the 320x200 grid (got %s)' % hi['ui'])
    c.check(hi['separate_ui'], 'hi-res did not put the HUD on its own layer')
    c.check(hi['ui_used'], 'nothing was drawn onto the hi-res HUD layer')
    c.check(hi['window'] == base['window'],
            'the window changed size with the render scale (%s vs %s)'
            % (hi['window'], base['window']))
    c.check(hi['car_w'] == base['car_w'] * 3,
            'the player car did not scale with the render resolution '
            '(%s vs %s)' % (hi['car_w'], base['car_w']))
    for shot in ('title_colours', 'race_colours'):
        c.check(hi[shot] > 8,
                'the hi-res %s frame is nearly blank (%d colours)'
                % (shot.split('_')[0], hi[shot]))
    c.note('scale 1: world %s, HUD drawn in place' % (base['world'],))
    c.note('scale 3: world %s, HUD on a %s layer, window %s either way'
           % (hi['world'], hi['ui'], hi['window']))
    return c.report()
