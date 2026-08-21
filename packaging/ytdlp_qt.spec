# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: one folder, no console, bundled yt-dlp + ffmpeg.

Build with:  pyinstaller packaging/ytdlp_qt.spec
Result:      dist/yt-dlp-qt/  -> zip this up
"""

from pathlib import Path

REPO_ROOT = Path(SPECPATH).parent
VENDOR = REPO_ROOT / "vendor"

# Copied verbatim as data rather than declared as binaries: these are standalone
# programs, and we do not want PyInstaller folding ffmpeg's DLLs into the app's own.
vendor_files = [(str(path), "vendor") for path in VENDOR.iterdir() if path.is_file()]

a = Analysis(
    [str(REPO_ROOT / "packaging" / "entry.py")],
    pathex=[str(REPO_ROOT / "src")],
    binaries=[],
    datas=vendor_files,
    hiddenimports=[],
    excludes=[
        # Qt modules we never touch; they add tens of megabytes each.
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtOpenGL",
        "tkinter",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="yt-dlp-qt",
    console=False,          # no console window when she double-clicks it
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,              # UPX makes antivirus false positives much more likely
    name="yt-dlp-qt",
)
