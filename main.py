#!/usr/bin/env python3
"""LATE APEX - a retro pseudo-3D racer for macOS."""

import os
import sys


def game_root():
    """Where the assets live.

    Running from source that is this file's directory; inside a PyInstaller
    bundle the data is unpacked to sys._MEIPASS instead.
    """
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS',
                       os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


ROOT = game_root()
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, ROOT)

USAGE = """LATE APEX

  --hires        render the world at 960x600 instead of 320x200
  --scale N      render scale, 1-4 (1 is the default chunky look)
  -h, --help     this message

The HUD and menus stay on the 320x200 grid whatever the scale, so the pixel
font never softens.
"""


def parse_scale(argv):
    """Reads the render scale from argv and puts it in the environment before
    anything imports the renderer, which reads it once at import time."""
    scale = None
    for i, arg in enumerate(argv):
        if arg in ('-h', '--help'):
            sys.stdout.write(USAGE)
            return None
        if arg == '--hires':
            scale = 3
        elif arg == '--scale' and i + 1 < len(argv):
            scale = argv[i + 1]
        elif arg.startswith('--scale='):
            scale = arg.split('=', 1)[1]
    if scale is not None:
        try:
            n = max(1, min(4, int(scale)))
        except ValueError:
            sys.stderr.write("--scale needs a number from 1 to 4\n")
            return False
        os.environ['LATE_APEX_SCALE'] = str(n)
    return True


def check_assets():
    need = [os.path.join(ROOT, 'assets', 'sprites', 'car_player_2n.png'),
            os.path.join(ROOT, 'assets', 'audio', 'music_menu.wav')]
    missing = [p for p in need if not os.path.exists(p)]
    if missing:
        sys.stderr.write(
            'Assets are missing. Generate them with:\n'
            '    python tools/gen_assets.py && python tools/gen_music.py\n')
        return False
    return True


def main():
    parsed = parse_scale(sys.argv[1:])
    if parsed is None:
        return 0
    if parsed is False:
        return 2
    if not check_assets():
        return 1
    from game.app import App
    App(ROOT).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
