#!/bin/bash
# Builds "Late Apex.app" - a double-clickable wrapper around main.py.
#
# The bundle executable is a small universal (arm64 + x86_64) Mach-O launcher
# compiled from tools/launcher/launcher.c, not a shell script: a script has no
# Mach-O header for Finder to read, which is why script-based bundles get
# labelled "Intel". It runs natively on Apple Silicon and hands over to the
# virtualenv's Python, which is itself arm64 there.
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
APP="$ROOT/Late Apex.app"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# ---- launcher ------------------------------------------------------------
EXE="$APP/Contents/MacOS/LateApex"
ARCHS=""
if command -v clang >/dev/null 2>&1; then
    for arch in arm64 x86_64; do
        if clang -arch "$arch" -E - </dev/null >/dev/null 2>&1; then
            ARCHS="$ARCHS -arch $arch"
        fi
    done
fi

if [ -n "$ARCHS" ]; then
    # shellcheck disable=SC2086
    clang $ARCHS -O2 -Wall -mmacosx-version-min=10.13 \
        -DFALLBACK_ROOT="\"$ROOT\"" \
        -o "$EXE" tools/launcher/launcher.c
    echo "Launcher architectures: $(lipo -archs "$EXE")"
else
    echo "clang not found - falling back to a script launcher." >&2
    cat > "$EXE" <<LAUNCH
#!/bin/bash
cd "$ROOT"
if [ ! -x .venv/bin/python ]; then
    osascript -e 'display dialog "Late Apex needs its Python environment.\n\nOpen Terminal in the game folder and run:\n    ./run.sh" buttons {"OK"} with title "Late Apex" with icon caution'
    exit 1
fi
exec .venv/bin/python main.py
LAUNCH
fi
chmod +x "$EXE"

# ---- icon ----------------------------------------------------------------
if [ -f assets/icon.png ]; then
    ICONSET="$(mktemp -d)/icon.iconset"
    mkdir -p "$ICONSET"
    for sz in 16 32 64 128 256 512; do
        sips -z $sz $sz assets/icon.png --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
        sips -z $((sz*2)) $((sz*2)) assets/icon.png \
             --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
    done
    iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns"
    rm -rf "$(dirname "$ICONSET")"
fi

# ---- metadata ------------------------------------------------------------
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Late Apex</string>
  <key>CFBundleDisplayName</key><string>Late Apex</string>
  <key>CFBundleIdentifier</key><string>local.lateapex</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>LateApex</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.arcade-games</string>
  <key>LSMinimumSystemVersion</key><string>10.13</string>
  <key>LSArchitecturePriority</key>
  <array><string>arm64</string><string>x86_64</string></array>
</dict>
</plist>
PLIST

# ---- sign ----------------------------------------------------------------
# arm64 binaries must carry at least an ad-hoc signature to run at all.
codesign --force --deep --sign - "$APP" 2>/dev/null \
    && echo "Signed (ad-hoc)." \
    || echo "Warning: could not codesign the bundle." >&2

touch "$APP"
echo "Built: $APP"
