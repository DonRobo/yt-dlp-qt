"""Download the yt-dlp and ffmpeg binaries that get shipped inside the app.

Run before PyInstaller. Everything lands in ``vendor/`` next to the repo root,
which is where ``ytdlp_qt.binaries`` looks first.

    python tools/fetch_binaries.py --platform win64
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
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

# yt-dlp publishes its own ffmpeg builds, patched for the bugs that actually bite
# yt-dlp; they are what the project recommends. The "shared" variant is half the size
# of the static one because ffmpeg.exe and ffprobe.exe share their DLLs.
# YouTube requires a JavaScript runtime; deno is the one yt-dlp enables by
# default. Without it extraction is deprecated and formats can go missing.
DENO_URL = {
    "win64": (
        "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
    ),
    "linux64": (
        "https://github.com/denoland/deno/releases/latest/download/"
        "deno-x86_64-unknown-linux-gnu.zip"
    ),
}

FFMPEG_URL = {
    "win64": (
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-master-latest-win64-gpl-shared.zip"
    ),
}


def _api(path: str) -> dict:
    """Read the GitHub REST API, using the CI token when one is available."""
    request = urllib.request.Request(f"https://api.github.com/{path}")
    request.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:  # noqa: S310 - fixed host
        return json.load(response)


def upstream_versions(platform: str) -> dict[str, str]:
    """Identify exactly which upstream builds the URLs currently point at.

    Both downloads are rolling "latest" links, so a cache key has to be derived
    from what they resolve to right now, not from the URLs themselves.
    """
    versions = {
        "yt-dlp": _api("repos/yt-dlp/yt-dlp/releases/latest")["tag_name"],
        "deno": _api("repos/denoland/deno/releases/latest")["tag_name"],
    }
    if platform == "win64":
        wanted = FFMPEG_URL["win64"].rsplit("/", 1)[-1]
        release = _api("repos/yt-dlp/FFmpeg-Builds/releases/tags/latest")
        for asset in release["assets"]:
            if asset["name"] == wanted:
                versions["ffmpeg"] = asset["updated_at"]
                break
        else:
            raise SystemExit(f"{wanted} is not in the yt-dlp/FFmpeg-Builds latest release")
    return versions


def cache_key(platform: str) -> str:
    versions = upstream_versions(platform)
    digest = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
    return f"{platform}-{digest[:16]}"


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


def fetch_deno(platform: str) -> None:
    print("deno:")
    payload = download(DENO_URL[platform])
    name = "deno.exe" if platform == "win64" else "deno"
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            if Path(info.filename).name == name:
                target = VENDOR / name
                with archive.open(info) as source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
                make_executable(target)
                print(f"  -> {name} ({target.stat().st_size / 1e6:.1f} MB)")
                return
    raise SystemExit(f"{name} was not found in the deno archive")


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
    parser.add_argument(
        "--print-cache-key",
        action="store_true",
        help="print a key identifying the current upstream builds, then exit",
    )
    args = parser.parse_args()

    if args.print_cache_key:
        print(cache_key(args.platform))
        return 0

    VENDOR.mkdir(parents=True, exist_ok=True)
    fetch_ytdlp(args.platform)
    fetch_deno(args.platform)
    if args.platform == "win64":
        fetch_ffmpeg_windows()
    else:
        # Bundling ffmpeg on Linux would add ~128 MB for something every distribution
        # already packages, so the Linux build uses the system copy.
        print("ffmpeg: skipped on Linux — install it with your package manager.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
