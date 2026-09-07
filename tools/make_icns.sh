#!/bin/bash
# Converts assets/icon.png into assets/icon.icns.
set -e
cd "$(dirname "$0")/.."
[ -f assets/icon.png ] || { echo "assets/icon.png missing - run tools/gen_icon.py" >&2; exit 1; }
ICONSET="$(mktemp -d)/icon.iconset"
mkdir -p "$ICONSET"
for sz in 16 32 64 128 256 512; do
    sips -z $sz $sz assets/icon.png --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
    sips -z $((sz*2)) $((sz*2)) assets/icon.png --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o assets/icon.icns
rm -rf "$(dirname "$ICONSET")"
echo "Wrote assets/icon.icns"
