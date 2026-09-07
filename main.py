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
    if not check_assets():
        return 1
    from game.app import App
    App(ROOT).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
