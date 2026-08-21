"""The application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QStandardPaths, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .binaries import Tools
from .command import Job, Options, build_title_argv, parse_urls
from .formats import AUDIO_FORMATS, BROWSERS, CONTAINERS, VIDEO_CODECS
from .runner import QueueRunner, configure_no_window
from .settings import Settings

HINT_STYLE = "color: palette(mid);"
WARNING_STYLE = "color: #b26a00;"


def _default_directory() -> str:
    return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation) or str(
        Path.home()
    )


def _sanitise_filename(name: str) -> str:
    """Strip characters no common filesystem accepts."""
    for char in '<>:"/\\|?*':
        name = name.replace(char, "_")
    return name.strip().strip(".")[:150] or "download"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Downloader")
        self.settings = Settings()
        self.tools = Tools()
        self.runner: QueueRunner | None = None
        self.title_process: QProcess | None = None

        self._build_ui()
        self._restore_settings()
        self._update_mode()
        self._update_codec_warning()
        self._check_tools()

    # ---------------------------------------------------------------- building

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._build_status_widgets()

        layout.addWidget(self._build_urls())
        layout.addWidget(self._build_options())
        layout.addLayout(self._build_actions())
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.log_view, 1)

        self.setCentralWidget(central)
        self.resize(620, 520)

    def _build_urls(self) -> QWidget:
        box = QGroupBox("Link")
        layout = QVBoxLayout(box)

        self.url_edit = QPlainTextEdit()
        self.url_edit.setPlaceholderText("Paste a link here…")
        self.url_edit.setFixedHeight(80)
        self.url_edit.textChanged.connect(self._update_url_hint)
        layout.addWidget(self.url_edit)

        self.url_hint = QLabel()
        self.url_hint.setStyleSheet(HINT_STYLE)
        self.url_hint.setWordWrap(True)
        layout.addWidget(self.url_hint)
        return box

    def _build_options(self) -> QWidget:
        box = QGroupBox("Options")
        layout = QVBoxLayout(box)

        # Cookies
        cookies_row = QHBoxLayout()
        self.cookies_check = QCheckBox("Use cookies from browser")
        self.cookies_check.setToolTip(
            "Lets yt-dlp use your browser's login, for private or age-restricted videos.\n"
            "Close the browser first — it may lock its cookie database."
        )
        self.cookies_combo = QComboBox()
        for browser in BROWSERS:
            if browser == "safari" and sys.platform != "darwin":
                continue
            self.cookies_combo.addItem(browser.capitalize(), browser)
        self.cookies_combo.setEnabled(False)
        self.cookies_check.toggled.connect(self.cookies_combo.setEnabled)
        cookies_row.addWidget(self.cookies_check)
        cookies_row.addWidget(self.cookies_combo, 1)
        layout.addLayout(cookies_row)

        # Mode
        mode_row = QHBoxLayout()
        self.video_radio = QRadioButton("Video")
        self.audio_radio = QRadioButton("Audio only")
        self.video_radio.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.video_radio)
        self.mode_group.addButton(self.audio_radio)
        self.video_radio.toggled.connect(self._update_mode)
        mode_row.addWidget(self.video_radio)
        mode_row.addWidget(self.audio_radio)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        # Per-mode format settings
        self.format_stack = QStackedWidget()
        self.format_stack.addWidget(self._build_video_page())
        self.format_stack.addWidget(self._build_audio_page())
        layout.addWidget(self.format_stack)
        return box

    def _build_video_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        self.container_combo = QComboBox()
        for label, value in CONTAINERS:
            self.container_combo.addItem(label, value)
        form.addRow("File type:", self.container_combo)

        self.codec_combo = QComboBox()
        for label, preference, encoder in VIDEO_CODECS:
            self.codec_combo.addItem(label, (preference, encoder))
        self.codec_combo.currentIndexChanged.connect(self._update_codec_warning)
        form.addRow("Video codec:", self.codec_combo)
        layout.addLayout(form)

        self.codec_warning = QLabel(
            "Re-encoding runs the video through ffmpeg and can take much longer "
            "than the download itself."
        )
        self.codec_warning.setStyleSheet(WARNING_STYLE)
        self.codec_warning.setWordWrap(True)
        layout.addWidget(self.codec_warning)
        return page

    def _build_audio_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        self.audio_combo = QComboBox()
        for label, value in AUDIO_FORMATS:
            self.audio_combo.addItem(label, value)
        form.addRow("Convert to:", self.audio_combo)
        return page

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.download_button = QPushButton("Download…")
        self.download_button.setDefault(True)
        self.download_button.clicked.connect(self._on_download)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop)
        self.stop_button.hide()
        row.addStretch(1)
        row.addWidget(self.download_button)
        row.addWidget(self.stop_button)
        return row

    def _build_status_widgets(self) -> None:
        """Progress bar, status line and the collapsible log pane."""
        # Progress is reported as a fraction, so use a fine fixed range.
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet(HINT_STYLE)
        self.status_label.setWordWrap(True)

        self.log_button = QPushButton("Show details")
        self.log_button.setCheckable(True)
        self.log_button.setFlat(True)
        self.log_button.toggled.connect(self._toggle_log)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.hide()

    # ---------------------------------------------------------------- settings

    def _restore_settings(self) -> None:
        s = self.settings
        self.cookies_check.setChecked(s.get_bool("cookies/enabled", False))
        browser = s.get_str("cookies/browser", "firefox")
        index = self.cookies_combo.findData(browser)
        if index >= 0:
            self.cookies_combo.setCurrentIndex(index)

        if s.get_bool("mode/audio_only", False):
            self.audio_radio.setChecked(True)
        self.container_combo.setCurrentIndex(s.get_int("video/container", 0))
        self.codec_combo.setCurrentIndex(s.get_int("video/codec", 0))
        self.audio_combo.setCurrentIndex(s.get_int("audio/format", 0))
        self.log_button.setChecked(s.get_bool("ui/log_visible", False))
        self._update_url_hint()

    def _save_settings(self) -> None:
        s = self.settings
        s.set("cookies/enabled", self.cookies_check.isChecked())
        s.set("cookies/browser", self.cookies_combo.currentData())
        s.set("mode/audio_only", self.audio_radio.isChecked())
        s.set("video/container", self.container_combo.currentIndex())
        s.set("video/codec", self.codec_combo.currentIndex())
        s.set("audio/format", self.audio_combo.currentIndex())
        s.set("ui/log_visible", self.log_button.isChecked())
        s.sync()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._save_settings()
        super().closeEvent(event)

    # ------------------------------------------------------------ small updates

    def _check_tools(self) -> None:
        problem = self.tools.problem()
        if problem:
            self._append_log(f"WARNING: {problem}")
            QMessageBox.warning(self, "Missing program", problem)
            if self.tools.ytdlp is None:
                self.download_button.setEnabled(False)

    def _update_url_hint(self) -> None:
        count = len(parse_urls(self.url_edit.toPlainText()))
        if count > 1:
            self.url_hint.setText(
                f"{count} links — you will pick a folder, and they are downloaded one after "
                "another."
            )
        else:
            self.url_hint.setText(
                "One link per line. Paste several to download them one after another."
            )

    def _update_mode(self) -> None:
        self.format_stack.setCurrentIndex(0 if self.video_radio.isChecked() else 1)

    def _update_codec_warning(self) -> None:
        _, encoder = self.codec_combo.currentData()
        self.codec_warning.setVisible(encoder is not None)

    def _toggle_log(self, visible: bool) -> None:
        self.log_view.setVisible(visible)
        self.log_button.setText("Hide details" if visible else "Show details")

    def _append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def _current_options(self) -> Options:
        preference, encoder = self.codec_combo.currentData()
        return Options(
            audio_only=self.audio_radio.isChecked(),
            container=self.container_combo.currentData(),
            video_encoder=encoder,
            codec_preference=preference,
            audio_format=self.audio_combo.currentData(),
            cookies_browser=(
                self.cookies_combo.currentData() if self.cookies_check.isChecked() else None
            ),
            ffmpeg_dir=self.tools.ffmpeg_dir,
        )

    def _last_directory(self) -> str:
        directory = self.settings.get_str("paths/last_directory", "")
        if directory and Path(directory).is_dir():
            return directory
        return _default_directory()

    # ------------------------------------------------------------------ actions

    def _on_download(self) -> None:
        urls = parse_urls(self.url_edit.toPlainText())
        if not urls:
            QMessageBox.information(self, "No link", "Please paste at least one link first.")
            return
        if len(urls) == 1:
            self._fetch_title_then_ask(urls[0])
        else:
            self._ask_directory(urls)

    def _ask_directory(self, urls: list[str]) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Choose a folder for the downloads", self._last_directory()
        )
        if not directory:
            return
        self.settings.set("paths/last_directory", directory)
        jobs = [Job(url=url, directory=Path(directory)) for url in urls]
        self._start(jobs)

    def _fetch_title_then_ask(self, url: str) -> None:
        """Look up the title first so the Save-as dialog can suggest a filename."""
        assert self.tools.ytdlp is not None
        argv = build_title_argv(str(self.tools.ytdlp), url, self._current_options())

        self.download_button.setEnabled(False)
        self.download_button.setText("Fetching title…")

        process = QProcess(self)
        configure_no_window(process)
        self.title_process = process
        output: list[str] = []
        process.readyReadStandardOutput.connect(
            lambda: output.append(
                bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            )
        )
        process.readyReadStandardError.connect(
            lambda: self._append_log(
                bytes(process.readAllStandardError()).decode("utf-8", errors="replace").rstrip()
            )
        )

        def done(exit_code: int, _status) -> None:
            self.download_button.setEnabled(True)
            self.download_button.setText("Download…")
            self.title_process = None
            process.deleteLater()
            title = "".join(output).strip().splitlines()
            suggestion = _sanitise_filename(title[0]) if title and exit_code == 0 else "download"
            self._ask_filename(url, suggestion)

        process.finished.connect(done)
        process.start(argv[0], argv[1:])

    def _ask_filename(self, url: str, suggestion: str) -> None:
        start = str(Path(self._last_directory()) / suggestion)
        path, _ = QFileDialog.getSaveFileName(self, "Save as", start)
        if not path:
            return
        chosen = Path(path)
        self.settings.set("paths/last_directory", str(chosen.parent))
        # The extension is decided by yt-dlp and its post-processors, so only the
        # stem is ours to keep.
        self._start([Job(url=url, directory=chosen.parent, stem=chosen.stem)])

    def _start(self, jobs: list[Job]) -> None:
        self.log_view.clear()
        self.download_button.hide()
        self.stop_button.show()
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting…")

        self.runner = QueueRunner(str(self.tools.ytdlp), self)
        self.runner.log.connect(self._append_log)
        self.runner.progress.connect(self._on_progress)
        self.runner.finished.connect(self._on_queue_finished)
        self.runner.start(jobs, self._current_options())

    def _on_stop(self) -> None:
        self.stop_button.setEnabled(False)
        self.status_label.setText("Stopping…")
        if self.runner is not None:
            self.runner.stop()

    def _on_progress(
        self, index: int, total: int, fraction: float, speed: str, eta: str
    ) -> None:
        self.progress_bar.setValue(int(fraction * 1000))
        parts = [f"{index}/{total}"] if total > 1 else []
        parts.append(f"{fraction * 100:.0f}%")
        if speed:
            parts.append(speed)
        if eta and eta not in ("Unknown", "NA"):
            parts.append(f"ETA {eta}")
        self.status_label.setText(" · ".join(parts))

    def _on_queue_finished(self, succeeded: int, failed: list[str], stopped: bool) -> None:
        self.stop_button.hide()
        self.download_button.show()
        self.download_button.setEnabled(self.tools.ytdlp is not None)
        self.runner = None

        if stopped:
            self.progress_bar.setValue(0)
            self.status_label.setText("Stopped.")
            return

        self.progress_bar.setValue(1000)
        if failed:
            self.status_label.setText(f"Finished: {succeeded} done, {len(failed)} failed.")
            self.log_button.setChecked(True)
            QMessageBox.warning(
                self,
                "Some downloads failed",
                "These links could not be downloaded:\n\n"
                + "\n".join(failed[:10])
                + "\n\nSee the details pane for the reason.",
            )
        else:
            self.status_label.setText(f"Finished: {succeeded} download(s) saved.")
