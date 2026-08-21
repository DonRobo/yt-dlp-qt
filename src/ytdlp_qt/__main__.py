"""Entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import settings
from .mainwindow import MainWindow


def main() -> int:
    settings.init()
    app = QApplication(sys.argv)
    app.setApplicationName(settings.APPLICATION)
    app.setOrganizationName(settings.ORGANISATION)
    app.setApplicationDisplayName("Video Downloader")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
