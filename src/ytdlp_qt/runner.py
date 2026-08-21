"""Runs the download queue.

QProcess is asynchronous and signal-based, so the whole queue runs on the GUI
thread without a single worker thread: each process's ``finished`` signal starts
the next one.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QProcess, Signal

from .command import PROGRESS_PREFIX, Job, Options, build_argv

# Keeps a console window from flashing up for every child process on Windows.
CREATE_NO_WINDOW = 0x08000000


def configure_no_window(process: QProcess) -> None:
    if sys.platform != "win32":
        return

    def modifier(args) -> None:  # pragma: no cover - Windows only
        args.flags |= CREATE_NO_WINDOW

    process.setCreateProcessArgumentsModifier(modifier)


def _percent(text: str) -> float | None:
    text = text.strip().rstrip("%")
    try:
        return float(text) / 100.0
    except ValueError:
        return None


class QueueRunner(QObject):
    """Downloads a list of jobs one after another."""

    log = Signal(str)
    # index (1-based), total, overall fraction 0..1, speed, eta
    progress = Signal(int, int, float, str, str)
    # succeeded count, list of URLs that failed, whether the user stopped it
    finished = Signal(int, list, bool)

    def __init__(self, ytdlp: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ytdlp = ytdlp
        self._process: QProcess | None = None
        self._jobs: list[Job] = []
        self._options = Options()
        self._index = 0
        self._succeeded = 0
        self._failed: list[str] = []
        self._stopping = False
        self._buffer = ""

    @property
    def running(self) -> bool:
        return self._process is not None

    def start(self, jobs: list[Job], options: Options) -> None:
        if self.running:
            raise RuntimeError("a queue is already running")
        self._jobs = list(jobs)
        self._options = options
        self._index = 0
        self._succeeded = 0
        self._failed = []
        self._stopping = False
        self._start_next()

    def stop(self) -> None:
        """Abort the current download and drop the rest of the queue."""
        self._stopping = True
        if self._process is not None:
            # terminate() is unreliable for console programs on Windows.
            self._process.kill()

    def _start_next(self) -> None:
        if self._stopping or self._index >= len(self._jobs):
            self.finished.emit(self._succeeded, self._failed, self._stopping)
            self._jobs = []
            return

        job = self._jobs[self._index]
        argv = build_argv(self._ytdlp, job, self._options)

        self._buffer = ""
        process = QProcess(self)
        configure_no_window(process)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._on_output)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error)
        self._process = process

        self.log.emit(f"\n$ {' '.join(argv[1:])}\n")
        self.progress.emit(self._index + 1, len(self._jobs), self._overall(0.0), "", "")
        process.start(argv[0], argv[1:])

    def _overall(self, current_fraction: float) -> float:
        total = len(self._jobs)
        if total == 0:
            return 0.0
        return (self._index + current_fraction) / total

    def _on_output(self) -> None:
        if self._process is None:
            return
        data = bytes(self._process.readAllStandardOutput())
        self._buffer += data.decode("utf-8", errors="replace")
        # yt-dlp still emits a bare \r for some lines even with --newline.
        self._buffer = self._buffer.replace("\r\n", "\n").replace("\r", "\n")
        *lines, self._buffer = self._buffer.split("\n")
        for line in lines:
            self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        if line.startswith(PROGRESS_PREFIX):
            parts = line[len(PROGRESS_PREFIX):].split("\t")
            parts += [""] * (3 - len(parts))
            fraction = _percent(parts[0])
            if fraction is not None:
                self.progress.emit(
                    self._index + 1,
                    len(self._jobs),
                    self._overall(fraction),
                    parts[1].strip(),
                    parts[2].strip(),
                )
            return
        if line.strip():
            self.log.emit(line)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.log.emit(f"ERROR: could not start {self._ytdlp}")

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if self._buffer.strip():
            self._handle_line(self._buffer)
            self._buffer = ""

        job = self._jobs[self._index] if self._index < len(self._jobs) else None
        crashed = exit_status == QProcess.ExitStatus.CrashExit
        if self._stopping:
            self.log.emit("Stopped.")
        elif exit_code == 0 and not crashed:
            self._succeeded += 1
        elif job is not None:
            self._failed.append(job.url)
            self.log.emit(f"FAILED: {job.url} (exit code {exit_code})")

        if self._process is not None:
            self._process.deleteLater()
            self._process = None
        self._index += 1
        self._start_next()
