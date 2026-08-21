"""Locating yt-dlp, ffmpeg and ffprobe.

Bundled copies in ``vendor/`` win over whatever is on PATH, so the Windows zip
behaves identically on a machine that has never seen Python.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


def _vendor_dirs() -> list[Path]:
    """Every place a bundled binary might live, most specific first."""
    dirs: list[Path] = []
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: next to the exe. onefile: the unpacked temp dir.
        dirs.append(Path(sys.executable).parent / "vendor")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass) / "vendor")
    else:
        # Running from a source checkout: <repo>/vendor
        dirs.append(Path(__file__).resolve().parents[2] / "vendor")
    return dirs


def find(name: str) -> Path | None:
    """Return the path to ``name``, preferring a bundled copy over PATH."""
    filename = name + EXE_SUFFIX
    for directory in _vendor_dirs():
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    found = shutil.which(name)
    return Path(found) if found else None


class Tools:
    """Resolved locations of the external programs we drive."""

    def __init__(self) -> None:
        self.ytdlp = find("yt-dlp")
        self.ffmpeg = find("ffmpeg")
        self.ffprobe = find("ffprobe")

    @property
    def ffmpeg_dir(self) -> str | None:
        """What to hand to ``--ffmpeg-location`` (yt-dlp accepts a directory)."""
        return str(self.ffmpeg.parent) if self.ffmpeg else None

    def problem(self) -> str | None:
        """A user-facing message if something essential is missing, else None."""
        if self.ytdlp is None:
            return (
                "yt-dlp was not found. Reinstall the application, or install yt-dlp "
                "and make sure it is on your PATH."
            )
        if self.ffmpeg is None:
            return (
                "ffmpeg was not found. Downloads will still work, but merging video "
                "with audio and converting formats will fail."
            )
        return None
