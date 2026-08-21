"""Zip up a PyInstaller build for release.

Used instead of `zip`/`Compress-Archive` so both platforms produce an identical
layout, and — importantly — so the executable bit survives on Linux. Python's
zipfile drops permissions unless they are written into the archive by hand.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ytdlp_qt import __version__  # noqa: E402


def add(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = zipfile.ZipInfo.from_file(path, arcname)
    info.compress_type = zipfile.ZIP_DEFLATED
    # The high 16 bits of external_attr hold the unix mode; without this every
    # extracted file comes out non-executable.
    info.external_attr = (stat.S_IMODE(path.stat().st_mode) & 0xFFFF) << 16
    with path.open("rb") as source:
        archive.writestr(info, source.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, help="label used in the archive name")
    parser.add_argument("--dist", default="dist/yt-dlp-qt", help="folder to package")
    args = parser.parse_args()

    source = REPO_ROOT / args.dist
    if not source.is_dir():
        raise SystemExit(f"{source} does not exist — run pyinstaller first")

    name = f"yt-dlp-qt-{__version__}-{args.platform}.zip"
    target = REPO_ROOT / name
    # Everything lives under one folder, so extracting never litters the desktop.
    root = f"yt-dlp-qt-{__version__}"

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                add(archive, path, f"{root}/{path.relative_to(source).as_posix()}")

    size = target.stat().st_size / 1e6
    print(f"{name}  ({size:.0f} MB)")

    # Hand the filename to the workflow's later steps.
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"archive={name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
