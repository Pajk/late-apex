"""Shared setup for the test suite: headless pygame, an isolated scores file,
and helpers for building contact sheets of rendered frames."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, 'tests', 'output')

_scores_dir = None


def setup():
    """Must be called before importing anything from `game`."""
    global _scores_dir
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    # keep the suite away from the player's real high score table
    _scores_dir = tempfile.mkdtemp(prefix='turbo-test-scores-')
    os.environ['LATE_APEX_DATA_DIR'] = _scores_dir
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    os.makedirs(OUTPUT, exist_ok=True)

    import pygame
    pygame.init()
    from game.render import WIDTH, HEIGHT
    pygame.display.set_mode((WIDTH, HEIGHT))
    return pygame


def silent_audio():
    from game.app import _SilentAudio
    return _SilentAudio()


def contact_sheet(frames, path, cols=2):
    """Tile frames into one PNG so a human can eyeball a run afterwards."""
    import pygame
    if not frames:
        return None
    w, h = frames[0].get_size()
    rows = (len(frames) + cols - 1) // cols
    sheet = pygame.Surface((cols * w, rows * h))
    sheet.fill((16, 16, 20))
    for i, f in enumerate(frames):
        sheet.blit(f, ((i % cols) * w, (i // cols) * h))
    out = os.path.join(OUTPUT, path)
    pygame.image.save(sheet, out)
    return out


class Checks:
    """Minimal assertion collector - reports every failure, not just the
    first, so one run tells you everything that broke."""

    def __init__(self, name):
        self.name = name
        self.failures = []
        self.passed = 0
        self.notes = []

    def check(self, ok, message):
        if ok:
            self.passed += 1
        else:
            self.failures.append(message)
        return ok

    def near(self, value, lo, hi, message):
        return self.check(lo <= value <= hi,
                          '%s (got %.3f, expected %.3f..%.3f)'
                          % (message, value, lo, hi))

    def note(self, text):
        self.notes.append(text)

    def report(self):
        for n in self.notes:
            print('    %s' % n)
        if self.failures:
            print('  FAIL %s - %d passed, %d failed'
                  % (self.name, self.passed, len(self.failures)))
            for f in self.failures:
                print('    x %s' % f)
        else:
            print('  ok   %s - %d checks passed' % (self.name, self.passed))
        return not self.failures
