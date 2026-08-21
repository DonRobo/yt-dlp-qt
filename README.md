# Video Downloader (yt-dlp-qt)

A small desktop window around [yt-dlp](https://github.com/yt-dlp/yt-dlp), for people who
should not have to open a terminal.

- Paste one link, or many links at once (one per line) — they download one after another.
- Optionally use your browser's cookies, for private or age-restricted videos.
- **Video** or **Audio only**, with a format conversion in either mode (ffmpeg does the work).
- Pick where the file goes; the folder is remembered for next time.

## For Windows

Download `yt-dlp-qt-<version>-windows.zip` from the
[latest release](../../releases/latest), extract it anywhere, and double-click
**yt-dlp-qt.exe**. Nothing to install — yt-dlp and ffmpeg are inside the zip.

> **"Windows protected your PC"** appears the first time, because the program is not
> code-signed (a signing certificate costs money). Click **More info** → **Run anyway**.
> Some antivirus tools also flag freshly-built PyInstaller programs; this is a known false
> positive.

Keep the extracted folder together — `yt-dlp-qt.exe` needs the `_internal` folder next to it.

## For Linux

Either grab `yt-dlp-qt-<version>-linux.zip` from the
[latest release](../../releases/latest):

```sh
unzip yt-dlp-qt-*-linux.zip     # use unzip, not a GUI extractor that drops the +x bit
cd yt-dlp-qt-*/ && ./yt-dlp-qt
```

…or run it from a checkout:

```sh
./run.sh
```

The release zip bundles yt-dlp but uses **your distribution's ffmpeg** — bundling it would add
~128 MB for something every distribution already packages. Install it if you have not:
`sudo pacman -S ffmpeg` / `sudo apt install ffmpeg`. The app says so on startup if it is missing.

The zip is built on Ubuntu 22.04, so it needs glibc 2.35 or newer. On something older, use
`./run.sh`.

## How the options map to yt-dlp

| In the window | What actually runs |
| --- | --- |
| Use cookies from browser | `--cookies-from-browser <name>` |
| (always, when deno is bundled) | `--js-runtimes deno:<path>` |
| Audio only + *Best available* | `-x` |
| Audio only + MP3/WAV/… | `-x --audio-format mp3` |
| Video + *Keep original* + *Any* | `-f "bv*+ba/b"` |
| Video + MP4 + *Any* | `… --merge-output-format mp4 --remux-video mp4` (repackage, no re-encode — fast) |
| Video + MKV + H.265 | `… -S vcodec:h265 --recode-video mkv --postprocessor-args "VideoConvertor:-c:v libx265 -c:a aac"` |

Choosing a specific video codec means a real ffmpeg re-encode, which can easily take longer
than the download. Leaving it on **Any** just repackages the file and takes seconds.

**One link** opens a *Save as* dialog with the video's title pre-filled (the app fetches the
title first, which is the brief "Fetching title…" pause). **Several links** open a folder
picker instead, and each file is named after its title.

Settings live in an INI file in your user config directory
(`%APPDATA%\ytdlp-qt\` on Windows, `~/.config/ytdlp-qt/` on Linux) — not the registry, so the
extracted folder stays portable.

## Development

```sh
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest          # argv building + binary lookup, all offline
./run.sh
```

Layout:

| Path | Purpose |
| --- | --- |
| `src/ytdlp_qt/command.py` | UI state → yt-dlp argv. Pure, no Qt, fully unit-tested. |
| `src/ytdlp_qt/runner.py` | The download queue. `QProcess` signals drive it — no worker threads. |
| `src/ytdlp_qt/binaries.py` | Finds yt-dlp/ffmpeg: bundled `vendor/` first, then `PATH`. |
| `src/ytdlp_qt/mainwindow.py` | The window. |
| `tools/fetch_binaries.py` | Downloads the binaries that get shipped. |
| `packaging/ytdlp_qt.spec` | PyInstaller: one folder, no console window. |

### CI

| Workflow | Does what |
| --- | --- |
| `tests.yml` | pytest on Linux and Windows, plus one job on the oldest supported Python to keep `requires-python` honest, plus `ruff check`/`ruff format --check`. The suite imports no Qt, so it needs no PySide6 and finishes in seconds. |
| `build.yml` | Builds the Windows and Linux zips on every push, and cuts a release on a `v*` tag. |

The bundled binaries come from rolling "latest" URLs, so the build cache is keyed on what those
URLs currently resolve to (`fetch_binaries.py --print-cache-key`): a new upstream yt-dlp or
ffmpeg busts the cache, and nothing else does.

Renovate raises dependency PRs, with the build's Python version and PySide6 grouped into one —
the build can only move to a new Python once PySide6 has wheels for it, and the build job is
what enforces that. A bump that cannot work stays red and does not get merged.

### Cutting a release

1. Bump `__version__` in `src/ytdlp_qt/__init__.py` (the single source — `pyproject.toml` reads
   it, and the window title shows it).
2. Commit, then tag and push:

   ```sh
   git tag v0.2.0 && git push origin v0.2.0
   ```

The tagged build refuses to publish if the tag and `__version__` disagree, then attaches both
zips to a GitHub release with generated notes.

### Building by hand

```sh
pip install -e '.[dev]' pyinstaller
python tools/fetch_binaries.py --platform win64   # or linux64
pyinstaller --noconfirm packaging/ytdlp_qt.spec
python tools/package.py --platform windows        # or linux
```

YouTube serves obfuscated JavaScript that has to be executed to work out its signature
parameters. yt-dlp has deprecated doing that without a real JS runtime, so **deno** is bundled
too and passed via `--js-runtimes`; without it yt-dlp warns that formats may be missing.

The Windows zip is about 175 MB, most of it ffmpeg and deno. That buys a build with every encoder the
codec dropdown offers — x264, x265, VP9 and AV1 — using the
[ffmpeg builds yt-dlp publishes itself](https://github.com/yt-dlp/FFmpeg-Builds), which carry
the patches yt-dlp needs.

### If it does not work

Run the executable with `--self-test` from a terminal. It reports whether the build can find
and actually start its bundled yt-dlp and ffmpeg, and whether the window can be constructed:

```
yt-dlp-qt.exe --self-test
```

CI runs the same check against every build, because a packaging fault can leave the window
opening normally while every button is dead.

### Known limitations

- The bundled yt-dlp ages, and sites break it regularly. Rebuild to pick up a newer one.
- No resolution/quality picker, playlist options, or subtitles yet.

## A note on how this was written

This project was written by [Claude Code](https://claude.com/claude-code), an AI coding agent,
working from a feature description and reviewed by a human before release. The download,
conversion and packaging paths were each exercised for real — not only unit-tested — but treat
it as you would any small tool from the internet: read the source if it matters to you.

## Licence

This code is [MIT](LICENSE).

The bundled binaries keep their own: yt-dlp is Unlicense, and the bundled ffmpeg is a **GPL**
build, so distributing the Windows zip as a whole means distributing GPL software (which is
fine — it just means the ffmpeg source has to stay available, and
[yt-dlp/FFmpeg-Builds](https://github.com/yt-dlp/FFmpeg-Builds) provides it).
