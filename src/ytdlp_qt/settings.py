"""Persisted UI state.

An INI file in the user's config directory, so we neither touch the Windows
registry nor need the install folder to be writable.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, QStandardPaths

ORGANISATION = "ytdlp-qt"
APPLICATION = "ytdlp-qt"


def init() -> None:
    """Call once, before any QSettings instance is created."""
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation),
    )


class Settings:
    def __init__(self) -> None:
        self._s = QSettings(ORGANISATION, APPLICATION)

    def get_str(self, key: str, default: str = "") -> str:
        value = self._s.value(key, default)
        return str(value) if value is not None else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self._s.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self._s.value(key, default))
        except (TypeError, ValueError):
            return default

    def set(self, key: str, value: object) -> None:
        self._s.setValue(key, value)

    def sync(self) -> None:
        self._s.sync()
