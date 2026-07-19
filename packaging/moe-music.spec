# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — build with:  pyinstaller packaging/moe-music.spec --noconfirm
# Produces dist/JyMusic (onedir) and, on macOS, dist/Jy Music.app

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent  # noqa: F821 — SPECPATH is injected by PyInstaller

_version_ns = {}
exec((ROOT / "version.py").read_text(encoding="utf-8"), _version_ns)
APP_VERSION = _version_ns["__version__"]

# tkinterdnd2 ships native tkdnd libraries that PyInstaller misses without
# an explicit collect; it is an optional dep, so tolerate its absence.
datas, binaries, hiddenimports = [], [], []
try:
    d, b, h = collect_all("tkinterdnd2")
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    pass

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)

icon_file = str(ROOT / "packaging" / "assets" /
                ("icon.icns" if sys.platform == "darwin" else "icon.ico"))

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JyMusic",
    console=False,
    icon=icon_file if sys.platform != "linux" else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="JyMusic")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Jy Music.app",
        icon=icon_file,
        bundle_identifier="io.github.meachallouisjunyan.jymusic",
        info_plist={
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,
        },
    )
