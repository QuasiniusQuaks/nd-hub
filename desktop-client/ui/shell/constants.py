"""Shell constants (Issue #93)."""
from enum import IntEnum

VERSION = "0.5"


class UI:
    MIN_WINDOW_WIDTH = 1100
    MIN_WINDOW_HEIGHT = 700
    SIDEBAR_WIDTH = 240
    MAX_BACKUPS_DEFAULT = 10


class Cache:
    """Schneller UI-Hash-Speicher für Diff-Berechnungen."""

    def __init__(self):
        self._last_verfall_hash: str | None = None


class PageIndex(IntEnum):
    """Stack-Indizes für Navigation."""

    DASHBOARD = 0
    MOVEMENTS = 1
    HISTORIE = 2
    AUSWERTUNGEN = 3
    IMPORT = 4
    EMAIL = 5
    GRUNDEINSTELLUNGEN = 6
