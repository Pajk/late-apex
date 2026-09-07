#!/bin/bash
# Builds a self-contained "Late Apex.app" in dist/ that can be sent to
# someone else - the Python runtime, pygame and all assets are embedded, so
# the recipient needs nothing installed.
set -e
cd "$(dirname "$0")/.."

[ -x .venv/bin/python ] || { echo "Run ./run.sh first to create .venv" >&2; exit 1; }

if ! .venv/bin/python -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    .venv/bin/python -m pip install --quiet pyinstaller
fi

[ -f assets/icon.icns ] || ./tools/make_icns.sh

echo "Building (this takes a minute)..."
rm -rf build dist
.venv/bin/python -m PyInstaller --noconfirm --clean LateApex.spec

APP="dist/Late Apex.app"
[ -d "$APP" ] || { echo "Build failed: $APP not produced" >&2; exit 1; }

# arm64 binaries must be signed to run; ad-hoc is enough for a hand-delivered
# app, though the recipient still has to right-click > Open the first time
# because it is not notarized.
codesign --force --deep --sign - "$APP" 2>/dev/null \
    && echo "Signed (ad-hoc)." || echo "Warning: codesign failed." >&2

# Strip the quarantine flag from our own build artefacts.
xattr -cr "$APP" 2>/dev/null || true

echo
echo "Built:        $APP"
echo "Architecture: $(lipo -archs "$APP/Contents/MacOS/LateApex" 2>/dev/null)"
echo "Size:         $(du -sh "$APP" | cut -f1)"
echo
echo "To send it, zip it (this preserves the bundle and its signature):"
echo "    ditto -c -k --keepParent \"$APP\" ~/Desktop/LateApex.zip"
