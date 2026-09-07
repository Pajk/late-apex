"""Captures the screenshots and the gameplay GIF used in the README.

    python tools/capture.py

Needs Pillow (only for writing the GIF):  pip install pillow
Everything lands in docs/.
"""

import os
import random
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ROOT = os.path.abspath(ROOT)
sys.path.insert(0, ROOT)
os.environ.setdefault('LATE_APEX_DATA_DIR',
                      os.path.join(ROOT, 'docs', '.capture-scores'))

import pygame  # noqa: E402

from game import autopilot  # noqa: E402
from game import cars as garage  # noqa: E402
from game import track as T  # noqa: E402
from game.race import Race, MAX_SPEED  # noqa: E402
from game.render import Assets, Renderer, WIDTH, HEIGHT  # noqa: E402
from game.scores import Scores  # noqa: E402

DOCS = os.path.join(ROOT, 'docs')
SHOT_SCALE = 3
GIF_SCALE = 2
GIF_FPS = 20
GIF_SECONDS_PER_TRACK = 1.8


def upscale(surface, factor):
    return pygame.transform.scale(
        surface, (WIDTH * factor, HEIGHT * factor))


def to_pil(surface):
    from PIL import Image
    raw = pygame.image.tobytes(surface, 'RGB')
    return Image.frombytes('RGB', surface.get_size(), raw)


class Session:
    def __init__(self):
        pygame.init()
        pygame.display.set_mode((WIDTH, HEIGHT))
        self.assets = Assets(ROOT)
        self.renderer = Renderer(self.assets)
        self.scores = Scores(T.TRACK_SPECS)
        self.surface = pygame.Surface((WIDTH, HEIGHT)).convert()

    def race(self, key, seed=7, car=None):
        """A race posed mid-way through lap two, so the HUD in a screenshot
        shows the numbers a player would actually be looking at."""
        track = T.load(key)
        race = Race(track, self.renderer, _Silent(), self.scores,
                    random.Random(seed), car=car)
        race.state = Race.STATE_RACING
        race.player.speed = MAX_SPEED * 0.6
        race.player.lap = 1
        race.time_left = track.lap_bonus * 0.86
        race.lap_time = track.lap_bonus * 0.42
        race.best_lap = track.lap_bonus * 0.94
        race.lap_times = [race.best_lap]
        return race

    def settle(self, race, seconds, skill=0.92):
        for _ in range(int(seconds * 60)):
            race.update(1 / 60.0, autopilot.drive(race, skill))

    def frame(self, race, skill=0.92):
        race.update(1 / 60.0, autopilot.drive(race, skill))
        race.draw(self.surface)
        return self.surface


class _Silent:
    ok = False

    def play(self, *a, **k):
        pass

    def engine(self, *a, **k):
        pass

    def engine_off(self):
        pass

    def skid(self, *a, **k):
        pass

    def set_engine(self, *a, **k):
        pass

    def shift(self, *a, **k):
        pass

    def roar(self, *a, **k):
        pass

    def turbo(self, *a, **k):
        pass

    def play_music(self, *a, **k):
        pass

    def quiet(self):
        pass


def capture_tracks(session):
    """One representative still per circuit."""
    made = []
    for spec in T.TRACK_SPECS:
        race = session.race(spec['key'])
        session.settle(race, 14)
        # nudge forward until the shot has some scenery and a rival in view
        best, best_score = None, -1
        for _ in range(240):
            surf = session.frame(race)
            colours = len({surf.get_at((x, y))[:3]
                           for x in range(10, WIDTH, 11)
                           for y in range(30, HEIGHT - 34, 9)})
            cars = sum(len(s.cars) for s in race.track.segments[
                int(race.player.z / 200):int(race.player.z / 200) + 120])
            score = colours + cars * 22 + race.speed_ratio * 10
            if race.player.offroad:
                score -= 60
            if score > best_score:
                best_score, best = score, surf.copy()
        path = os.path.join(DOCS, 'track-%s.png' % spec['key'])
        pygame.image.save(upscale(best, SHOT_SCALE), path)
        made.append(path)
        print('  %s' % os.path.relpath(path, ROOT))
        race.clear()
    return made


def capture_menus():
    """Title, circuit select and the high score table, with the attract-mode
    demo running behind them exactly as a player sees it."""
    from game.app import App, S_SELECT, S_SCORES
    app = App(ROOT)
    made = []

    def step(n):
        for _ in range(n):
            app.update(1 / 60.0)
            app.draw()

    def shot(name):
        path = os.path.join(DOCS, name)
        pygame.image.save(upscale(app.screen, SHOT_SCALE), path)
        made.append(path)
        print('  %s' % os.path.relpath(path, ROOT))

    def press(key):
        app.on_key(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0,
                                      unicode=''))

    step(150)
    shot('title.png')
    press(pygame.K_RETURN)
    step(60)
    assert app.state == S_SELECT
    step(120)
    shot('select.png')
    press(pygame.K_RETURN)
    step(90)
    shot('difficulty.png')
    press(pygame.K_RETURN)
    step(90)
    shot('garage.png')
    press(pygame.K_ESCAPE)
    step(60)
    press(pygame.K_ESCAPE)
    step(60)
    press(pygame.K_h)
    step(60)
    assert app.state == S_SCORES
    shot('scores.png')
    return made


def capture_gif(session):
    """A montage across all five circuits - the variety is the point."""
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print('  (skipped: pip install pillow to build the GIF)')
        return None

    frames = []
    per_track = int(GIF_SECONDS_PER_TRACK * GIF_FPS)
    stride = max(1, int(round(60 / GIF_FPS)))
    for i, spec in enumerate(T.TRACK_SPECS):
        race = session.race(spec['key'], car=garage.CARS[i % len(garage.CARS)])
        session.settle(race, 16)
        for _ in range(per_track):
            for _ in range(stride):
                surf = session.frame(race)
            frames.append(to_pil(upscale(surf, GIF_SCALE)))
        race.clear()
        print('  %-14s %-12s %d frames'
              % (spec['name'], race.car['name'], per_track))

    path = os.path.join(DOCS, 'gameplay.gif')
    first, rest = frames[0], frames[1:]
    first.save(path, save_all=True, append_images=rest,
               duration=int(1000 / GIF_FPS), loop=0, optimize=True)
    size = os.path.getsize(path) / 1e6
    print('  %s (%d frames, %.1f MB)'
          % (os.path.relpath(path, ROOT), len(frames), size))
    return path


def main():
    os.makedirs(DOCS, exist_ok=True)
    session = Session()
    print('circuit stills:')
    capture_tracks(session)
    print('menus:')
    capture_menus()
    print('gameplay gif:')
    capture_gif(session)

    scratch = os.environ.get('LATE_APEX_DATA_DIR', '')
    if scratch.startswith(DOCS):
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)
    print('done')


if __name__ == '__main__':
    main()
