"""Entry point."""

from __future__ import annotations

import sys
import traceback
from types import TracebackType

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QMessageBox

from . import settings
from .mainwindow import MainWindow


def _show_unhandled_error(
    kind: type[BaseException], value: BaseException, tb: TracebackType | None
) -> None:
    """Report crashes instead of leaving the window silently wedged.

    An exception raised inside a Qt slot does not propagate anywhere useful: the
    click handler simply stops half-way, leaving buttons disabled and the window
    looking frozen with nothing to go on. Showing it costs one dialog and turns
    "it doesn't work" into an actual report.
    """
    details = "".join(traceback.format_exception(kind, value, tb))
    print(details, file=sys.stderr)
    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("Something went wrong")
    box.setText(f"{kind.__name__}: {value}")
    box.setInformativeText("The last action was cancelled. Details are below.")
    box.setDetailedText(details)
    box.exec()


def _run(argv: list[str], timeout_ms: int = 60000) -> tuple[int, str]:
    """Start a program exactly the way the app does, and wait for it."""
    process = QProcess()
    process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    process.start(argv[0], argv[1:])
    if not process.waitForStarted(timeout_ms) or not process.waitForFinished(timeout_ms):
        return -1, process.errorString()
    return process.exitCode(), bytes(process.readAll()).decode("utf-8", errors="replace").strip()


def self_test() -> int:
    """Check that this build can find and actually start its bundled programs.

    Exists because a packaging bug can leave every button dead while the window
    itself still opens — the kind of failure unit tests cannot see, since it only
    appears in the frozen build. CI runs this against the real executable.
    """
    from .binaries import Tools

    app = QApplication(sys.argv)
    failures: list[str] = []

    tools = Tools()
    for name in ("ytdlp", "ffmpeg", "ffprobe", "deno"):
        path = getattr(tools, name)
        print(f"{name}: {path or 'NOT FOUND'}")
        if path is None:
            failures.append(f"{name} was not found")

    for name, flag in (("ytdlp", "--version"), ("ffmpeg", "-version"), ("deno", "--version")):
        path = getattr(tools, name)
        if path is None:
            continue
        code, output = _run([str(path), flag])
        first = output.splitlines()[0] if output else "(no output)"
        print(f"start {name}: exit={code} {first}")
        if code != 0:
            failures.append(f"{name} could not be started: {first}")

    try:
        MainWindow().show()
        print("window: constructed")
    except Exception as error:  # the point is to report anything at all
        traceback.print_exc()
        failures.append(f"the window could not be built: {error}")

    app.quit()
    if failures:
        print("\nSELF-TEST FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nSELF-TEST PASSED")
    return 0


def main() -> int:
    settings.init()
    if "--self-test" in sys.argv:
        return self_test()
    sys.excepthook = _show_unhandled_error
    app = QApplication(sys.argv)
    app.setApplicationName(settings.APPLICATION)
    app.setOrganizationName(settings.ORGANISATION)
    app.setApplicationDisplayName("Video Downloader")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
