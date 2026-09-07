# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for a self-contained Late Apex.app.

Embeds the Python runtime, pygame and every generated asset, so the bundle
runs on a Mac with nothing installed. numpy is excluded deliberately: it is
only used by the asset generators in tools/, never by the game itself.
"""

import os

ROOT = os.path.abspath(os.getcwd())

a = Analysis(
    ['main.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'assets', 'sprites'), 'assets/sprites'),
        (os.path.join(ROOT, 'assets', 'audio'), 'assets/audio'),
    ],
    hiddenimports=['game', 'game.app', 'game.race', 'game.render',
                   'game.track', 'game.audio', 'game.scores',
                   'game.pixelfont'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['numpy', 'tkinter', 'unittest', 'pydoc', 'doctest',
              'email', 'html', 'http', 'xml', 'pdb', 'PIL',
              'setuptools', 'pip', 'distutils'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LateApex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=None,          # native arch of the building interpreter
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='LateApex',
)

app = BUNDLE(
    coll,
    name='Late Apex.app',
    icon=os.path.join(ROOT, 'assets', 'icon.icns'),
    bundle_identifier='local.lateapex',
    version='1.0',
    info_plist={
        'CFBundleName': 'Late Apex',
        'CFBundleDisplayName': 'Late Apex',
        'CFBundleShortVersionString': '1.0',
        'CFBundleVersion': '1.0',
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.arcade-games',
        'LSMinimumSystemVersion': '11.0',
        'NSRequiresAquaSystemAppearance': False,
    },
)
