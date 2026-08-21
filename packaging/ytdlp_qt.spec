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

def drop_duplicate_libraries(analysis):
    """Ship each bundled library once.

    PyInstaller reclassifies the ffmpeg DLLs in vendor/ as binaries and hoists a
    second copy to the top level. Only the vendor/ copies matter — that is where
    ffmpeg.exe looks for them — and nothing in this app links against them, so
    the hoisted set is pure duplication (~168 MB on Windows).
    """
    vendor_names = {
        Path(dest).name.lower()
        for dest, _src, _kind in list(analysis.binaries) + list(analysis.datas)
        if Path(dest).parts[:1] == ("vendor",)
    }

    def is_hoisted_vendor_copy(entry):
        dest = Path(entry[0])
        # A bare filename at the top level that vendor/ already provides.
        return not dest.parent.parts and dest.name.lower() in vendor_names

    for name in ("binaries", "datas"):
        entries = list(getattr(analysis, name))
        kept = [entry for entry in entries if not is_hoisted_vendor_copy(entry)]
        if len(kept) != len(entries):
            print(f"spec: dropped {len(entries) - len(kept)} hoisted vendor copies from {name}")
        setattr(analysis, name, kept)


drop_duplicate_libraries(a)

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
