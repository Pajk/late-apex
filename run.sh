#!/bin/bash
# Sets up a local virtualenv on first run, then starts the game.
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
VENV=".venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "Creating virtualenv..."
    "$PY" -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip >/dev/null
    "$VENV/bin/python" -m pip install -r requirements.txt
fi

if [ ! -f assets/sprites/car_player_2n.png ] || [ ! -f assets/audio/music_menu.wav ]; then
    echo "Generating assets..."
    "$VENV/bin/python" tools/gen_assets.py
    "$VENV/bin/python" tools/gen_music.py
fi

exec "$VENV/bin/python" main.py "$@"
