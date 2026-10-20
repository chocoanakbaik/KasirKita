# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build for a conventional Windows application package.

Keeping the executable and its runtime files in a directory avoids the
one-file self-extraction behavior that can contribute to antivirus false
positives and makes the packaged files easier to inspect.
"""
from pathlib import Path

ROOT = Path(SPECPATH)
ASSETS = ROOT / "assets"

datas = []
if ASSETS.exists():
    datas.append((str(ASSETS), "assets"))

a = Analysis(
    ["kasirkita/__main__.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["PIL", "PIL.Image", "PIL.ImageTk", "barcode", "barcode.writer"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "jupyter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KasirKita",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ASSETS / "icons" / "kasirkita.ico"),
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KasirKita",
)
