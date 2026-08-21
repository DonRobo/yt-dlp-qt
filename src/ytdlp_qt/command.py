"""Turns the UI state into a yt-dlp argv.

Deliberately free of Qt imports so it can be unit-tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .formats import DEFAULT_CONTAINER_FOR_CODEC

# Prefix + separator we use to recognise our own progress lines in the output stream.
PROGRESS_PREFIX = "PROG\t"
PROGRESS_TEMPLATE = (
    "download:" + PROGRESS_PREFIX + "%(progress._percent_str)s\t"
    "%(progress._speed_str)s\t%(progress._eta_str)s"
)


@dataclass
class Options:
    """Everything the user can configure in the window."""

    audio_only: bool = False
    # Video mode
    container: str | None = None  # mp4 / mkv / webm, or None to keep the original
    video_encoder: str | None = None  # ffmpeg encoder, e.g. libx264. None = no re-encode
    codec_preference: str | None = None  # -S vcodec: value, e.g. h264
    # Audio mode
    audio_format: str | None = None  # mp3 / m4a / ..., or None for no conversion
    # Shared
    cookies_browser: str | None = None
    ffmpeg_dir: str | None = None


@dataclass
class Job:
    """One download: where it goes and, in single-URL mode, under what name."""

    url: str
    directory: Path
    # Filename without extension. None in batch mode, where the title is used instead.
    stem: str | None = None
    extra_args: list[str] = field(default_factory=list)


def _escape_template_literal(text: str) -> str:
    """Make a user-supplied filename safe to embed in a yt-dlp output template."""
    return text.replace("%", "%%")


def output_template(job: Job) -> str:
    stem = _escape_template_literal(job.stem) if job.stem is not None else "%(title)s"
    return str(job.directory / f"{stem}.%(ext)s")


def build_argv(ytdlp: str, job: Job, options: Options) -> list[str]:
    """Build the full command line for a single download."""
    argv = [
        ytdlp,
        "--ignore-config",  # a stray ~/.config/yt-dlp/config must not change our behaviour
        "--newline",
        "--no-color",
        "--progress",
        "--progress-template",
        PROGRESS_TEMPLATE,
        "-o",
        output_template(job),
    ]

    if job.stem is not None:
        # She named one specific file, so a playlist URL must not fill it repeatedly.
        argv.append("--no-playlist")

    if options.ffmpeg_dir:
        argv += ["--ffmpeg-location", options.ffmpeg_dir]

    if options.cookies_browser:
        argv += ["--cookies-from-browser", options.cookies_browser]

    if options.audio_only:
        argv.append("-x")
        if options.audio_format:
            argv += ["--audio-format", options.audio_format]
    else:
        argv += ["-f", "bv*+ba/b"]

        if options.codec_preference:
            argv += ["-S", f"vcodec:{options.codec_preference}"]

        if options.video_encoder:
            # A real ffmpeg re-encode. --recode-video needs a container that fits the codec.
            container = options.container or DEFAULT_CONTAINER_FOR_CODEC[options.video_encoder]
            argv += ["--merge-output-format", container]
            argv += ["--recode-video", container]
            argv += [
                "--postprocessor-args",
                f"VideoConvertor:-c:v {options.video_encoder} -c:a aac",
            ]
        elif options.container:
            # Container change only, no re-encode.
            argv += ["--merge-output-format", options.container]
            argv += ["--remux-video", options.container]

    argv += job.extra_args
    argv.append(job.url)
    return argv


def build_title_argv(ytdlp: str, url: str, options: Options) -> list[str]:
    """Command that prints just the title, used to pre-fill the Save-as dialog."""
    argv = [
        ytdlp,
        "--ignore-config",
        "--no-color",
        "--skip-download",
        "--no-playlist",
        "--playlist-items",
        "1",
        "--print",
        "%(title)s",
    ]
    if options.cookies_browser:
        argv += ["--cookies-from-browser", options.cookies_browser]
    argv.append(url)
    return argv


def parse_urls(text: str) -> list[str]:
    """One URL per line; blank lines and #-comments ignored."""
    urls = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls
