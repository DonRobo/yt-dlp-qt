# Video Downloader (yt-dlp-qt)

A small desktop window around [yt-dlp](https://github.com/yt-dlp/yt-dlp), for people who
should not have to open a terminal.

- Paste one link, or many links at once (one per line) — they download one after another.
- Optionally use your browser's cookies, for private or age-restricted videos.
- **Video** or **Audio only**, with a format conversion in either mode (ffmpeg does the work).
- Pick where the file goes; the folder is remembered for next time.

## For Windows

Download `yt-dlp-qt-windows.zip` from the
[latest release](../../releases/latest), extract it anywhere, and double-click
**yt-dlp-qt.exe**. Nothing to install — yt-dlp and ffmpeg are inside the zip.

> **"Windows protected your PC"** appears the first time, because the program is not
> code-signed (a signing certificate costs money). Click **More info** → **Run anyway**.
> Some antivirus tools also flag freshly-built PyInstaller programs; this is a known false
> positive.

Keep the extracted folder together — `yt-dlp-qt.exe` needs the `_internal` folder next to it.

## For Linux

```sh
./run.sh
```

Creates a virtualenv on first run. Uses the `yt-dlp` and `ffmpeg` from your package manager.

## How the options map to yt-dlp

| In the window | What actually runs |
| --- | --- |
| Use cookies from browser | `--cookies-from-browser <name>` |
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

### Building the Windows zip

Push to GitHub; `.github/workflows/build-windows.yml` builds on `windows-latest` and uploads
the zip as a workflow artifact. Tagging `v*` also attaches it to a GitHub release.

To build by hand on a Windows machine:

```
pip install -e .[dev] pyinstaller
python tools/fetch_binaries.py --platform win64
pyinstaller --noconfirm packaging/ytdlp_qt.spec
```

The zip is around 125 MB, most of it ffmpeg (~86 MB compressed). That buys a build with every
encoder the codec dropdown offers, including x264, x265, VP9 and AV1.

### Known limitations

- The bundled yt-dlp ages, and sites break it regularly. Rebuild to pick up a newer one.
- No resolution/quality picker, playlist options, or subtitles yet.
