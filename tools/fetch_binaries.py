"""Download the yt-dlp and ffmpeg binaries that get shipped inside the app.

Run before PyInstaller. Everything lands in ``vendor/`` next to the repo root,
which is where ``ytdlp_qt.binaries`` looks first.

    python tools/fetch_binaries.py --platform win64
"""

from __future__ import annotations

import argparse
import io
import shutil
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR = REPO_ROOT / "vendor"

YTDLP_URL = {
    "win64": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
    "linux64": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux",
}
YTDLP_NAME = {"win64": "yt-dlp.exe", "linux64": "yt-dlp"}

# The "shared" builds are a fraction of the size of the static ones because
# ffmpeg.exe and ffprobe.exe share their DLLs instead of embedding everything twice.
FFMPEG_URL = {
    "win64": (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-master-latest-win64-gpl-shared.zip"
    ),
    "linux64": (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-master-latest-linux64-gpl-shared.tar.xz"
    ),
}


def download(url: str) -> bytes:
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as response:  # noqa: S310 - fixed, trusted URLs
        return response.read()


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def fetch_ytdlp(platform: str) -> None:
    print("yt-dlp:")
    target = VENDOR / YTDLP_NAME[platform]
    target.write_bytes(download(YTDLP_URL[platform]))
    make_executable(target)
    print(f"  -> {target.name} ({target.stat().st_size / 1e6:.1f} MB)")


def fetch_ffmpeg_windows() -> None:
    print("ffmpeg:")
    payload = download(FFMPEG_URL["win64"])
    wanted = ("ffmpeg.exe", "ffprobe.exe")
    count = 0
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            name = Path(info.filename).name
            # The shared build needs its DLLs next to the executables.
            if Path(info.filename).parent.name != "bin":
                continue
            if name not in wanted and not name.lower().endswith(".dll"):
                continue
            with archive.open(info) as source, (VENDOR / name).open("wb") as target:
                shutil.copyfileobj(source, target)
            count += 1
    if not any((VENDOR / name).exists() for name in wanted):
        raise SystemExit("ffmpeg.exe/ffprobe.exe were not found in the archive")
    print(f"  -> {count} files extracted into vendor/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["win64", "linux64"], default="win64")
    args = parser.parse_args()

    VENDOR.mkdir(parents=True, exist_ok=True)
    fetch_ytdlp(args.platform)
    if args.platform == "win64":
        fetch_ffmpeg_windows()
    else:
        print("ffmpeg: skipped — install it from your distribution's package manager.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
