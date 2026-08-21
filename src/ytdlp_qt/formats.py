"""Format tables shown in the UI.

Each table maps the label the user sees to the value we hand to yt-dlp.
A value of ``None`` always means "don't pass the option at all".
"""

from __future__ import annotations

# --cookies-from-browser. Taken from `yt-dlp --help`; safari is macOS-only.
BROWSERS = ["brave", "chrome", "chromium", "edge", "firefox", "opera", "safari", "vivaldi", "whale"]

# (label, --merge-output-format / --remux-video value)
CONTAINERS: list[tuple[str, str | None]] = [
    ("Keep original", None),
    ("MP4", "mp4"),
    ("MKV (Matroska)", "mkv"),
    ("WebM", "webm"),
]

# (label, -S vcodec: preference, ffmpeg encoder for a forced re-encode)
VIDEO_CODECS: list[tuple[str, str | None, str | None]] = [
    ("Any (no re-encode, fastest)", None, None),
    ("H.264 / AVC", "h264", "libx264"),
    ("H.265 / HEVC", "h265", "libx265"),
    ("VP9", "vp9", "libvpx-vp9"),
    ("AV1", "av1", "libsvtav1"),
]

# (label, --audio-format value)
AUDIO_FORMATS: list[tuple[str, str | None]] = [
    ("Best available (no conversion)", None),
    ("MP3", "mp3"),
    ("M4A / AAC", "m4a"),
    ("Opus", "opus"),
    ("FLAC (lossless)", "flac"),
    ("WAV (uncompressed)", "wav"),
]

# A forced re-encode has to land in a container that can actually hold the codec.
# Used when the user picked a codec but left the container on "Keep original".
DEFAULT_CONTAINER_FOR_CODEC = {
    "libx264": "mp4",
    "libx265": "mp4",
    "libvpx-vp9": "webm",
    "libsvtav1": "mkv",
}
