"""The bundled-binary lookup, including the frozen (PyInstaller) layout."""

from __future__ import annotations

import sys

import pytest

from ytdlp_qt import binaries


@pytest.fixture
def fake_bundle(tmp_path, monkeypatch):
    """Pretend we are a PyInstaller onedir build with a populated vendor/."""
    internal = tmp_path / "_internal"
    vendor = internal / "vendor"
    vendor.mkdir(parents=True)
    (tmp_path / "yt-dlp-qt").write_text("")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(internal), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "yt-dlp-qt"))
    return vendor


def test_finds_binary_in_onedir_internal_vendor(fake_bundle, monkeypatch):
    monkeypatch.setattr(binaries, "EXE_SUFFIX", "")
    (fake_bundle / "ffmpeg").write_text("")
    assert binaries.find("ffmpeg") == fake_bundle / "ffmpeg"


def test_bundled_copy_wins_over_path(fake_bundle, monkeypatch):
    monkeypatch.setattr(binaries, "EXE_SUFFIX", "")
    monkeypatch.setattr(binaries.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    (fake_bundle / "ffmpeg").write_text("")
    assert binaries.find("ffmpeg") == fake_bundle / "ffmpeg"


def test_falls_back_to_path_when_not_bundled(fake_bundle, monkeypatch):
    monkeypatch.setattr(binaries, "EXE_SUFFIX", "")
    monkeypatch.setattr(binaries.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    assert binaries.find("ffmpeg") == binaries.Path("/usr/bin/ffmpeg")


def test_missing_everywhere_returns_none(fake_bundle, monkeypatch):
    monkeypatch.setattr(binaries, "EXE_SUFFIX", "")
    monkeypatch.setattr(binaries.shutil, "which", lambda name: None)
    assert binaries.find("nope") is None


def test_windows_suffix_is_used_for_the_lookup(fake_bundle, monkeypatch):
    monkeypatch.setattr(binaries, "EXE_SUFFIX", ".exe")
    monkeypatch.setattr(binaries.shutil, "which", lambda name: None)
    (fake_bundle / "yt-dlp.exe").write_text("")
    assert binaries.find("yt-dlp") == fake_bundle / "yt-dlp.exe"


def test_problem_message_reports_a_missing_ytdlp(monkeypatch):
    monkeypatch.setattr(binaries, "find", lambda name: None)
    assert "yt-dlp" in (binaries.Tools().problem() or "")


def test_no_problem_when_everything_is_present(monkeypatch):
    monkeypatch.setattr(binaries, "find", lambda name: binaries.Path(f"/usr/bin/{name}"))
    tools = binaries.Tools()
    assert tools.problem() is None
    assert tools.ffmpeg_dir == str(binaries.Path("/usr/bin"))
    assert tools.js_runtime == f"deno:{binaries.Path('/usr/bin/deno')}"


def test_js_runtime_is_none_without_deno(monkeypatch):
    monkeypatch.setattr(
        binaries, "find", lambda name: None if name == "deno" else binaries.Path(f"/usr/bin/{name}")
    )
    tools = binaries.Tools()
    # Missing deno degrades YouTube but must not block the app.
    assert tools.js_runtime is None
    assert tools.problem() is None
