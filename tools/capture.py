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
from game import difficulty as levels  # noqa: E402
from game import pixelfont as pf  # noqa: E402
from game import track as T  # noqa: E402
from game.race import Race, MAX_SPEED  # noqa: E402
from game.render import Assets, Renderer, WIDTH, HEIGHT  # noqa: E402
from game.scores import Scores  # noqa: E402

DOCS = os.path.join(ROOT, 'docs')
SHOT_SCALE = 3
GIF_SCALE = 2
GIF_FPS = 20
GIF_SECONDS_PER_TRACK = 1.6


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

    def race(self, key, seed=7, car=None, level=None):
        """A race posed mid-way through lap two, so the HUD in a screenshot
        shows the numbers a player would actually be looking at."""
        track = T.load(key)
        race = Race(track, self.renderer, _Silent(), self.scores,
                    random.Random(seed), car=car, level=level)
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


# What the montage shows: circuit, difficulty, car. Deliberately mixed so the
# oncoming-traffic levels and the odder vehicles both get screen time.
GIF_REEL = [
    ('country', 'easy', 'wedge'),
    ('city', 'medium', 'gt'),
    ('desert', 'hard', 'f1'),
    ('summer', 'medium', 'ambulance'),
    ('winter', 'hard', 'bike'),
    ('country', 'medium', 'coupe'),
]


VIEW = 16000


def _traffic_ahead(race):
    """How much oncoming traffic is worth showing, weighted towards cars that
    are close: a speck on the horizon does not demonstrate anything."""
    length = race.track.length
    score = 0.0
    for c in race.traffic:
        gap = (c.z - race.player.z) % length
        if 0 < gap < VIEW:
            score += (1.0 - gap / VIEW) ** 2
    return score


def capture_gif(session):
    """A montage across circuits, difficulties and cars.

    Two passes per segment: the first drives the whole stretch recording where
    the oncoming traffic actually is, the second replays from the best window
    so the traffic levels are shown carrying traffic rather than an empty road.
    """
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print('  (skipped: pip install pillow to build the GIF)')
        return None

    frames = []
    per_track = int(GIF_SECONDS_PER_TRACK * GIF_FPS)
    stride = max(1, int(round(60 / GIF_FPS)))
    scan = per_track * 4

    for circuit, level_key, car_key in GIF_REEL:
        level = levels.get(level_key)
        car = garage.get(car_key)
        label = '%s   %s' % (level['name'], car['name'])

        def fresh():
            race = session.race(circuit, car=car, level=level)
            session.settle(race, 15)
            return race

        # pass one: where is the traffic?
        race = fresh()
        counts = []
        for _ in range(scan):
            for _ in range(stride):
                session.frame(race)
            counts.append(_traffic_ahead(race))
        race.clear()

        start = 0
        if any(counts):
            windows = [(sum(counts[i:i + per_track]), i)
                       for i in range(len(counts) - per_track)]
            start = max(windows)[1] if windows else 0

        # pass two: replay and capture from there
        race = fresh()
        for _ in range(start * stride):
            session.frame(race)
        seen = 0
        for _ in range(per_track):
            for _ in range(stride):
                surf = session.frame(race)
            seen = max(seen, _traffic_ahead(race))
            shot = surf.copy()
            pf.draw_text(shot, label, 4, 28, (235, 238, 248), 1,
                         shadow=(10, 10, 20))
            frames.append(to_pil(upscale(shot, GIF_SCALE)))
        print('  %-9s %-7s %-12s %d frames, closest-traffic score %.2f'
              % (circuit, level['name'], car['name'], per_track, seen))
        race.clear()

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
