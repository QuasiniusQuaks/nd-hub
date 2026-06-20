"""Cross-Filter-State — Singleton für Cross-Chart-Filtering.

Wenn ein User auf ein Element in einem Chart klickt (z.B. "Depot A"),
werden alle anderen Charts gefiltert. Dieser State hält die aktiven
Filter zentral und benachrichtigt alle registrierten Listener.

Issue #42 Phase 1 — Cross-Filtering-Infrastruktur.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FilterState:
    """Zustand der aktiven Cross-Filter."""

    depot_ids: set[int] = field(default_factory=set)
    praeparat_ids: set[int] = field(default_factory=set)
    date_range_days: int = 30  # 7, 30, 90, 365

    def is_empty(self) -> bool:
        """True wenn kein Filter aktiv ist."""
        return not self.depot_ids and not self.praeparat_ids

    def clear(self) -> None:
        """Setzt alle Filter zurück."""
        self.depot_ids.clear()
        self.praeparat_ids.clear()
        self.date_range_days = 30


class CrossFilterState:
    """Singleton, das den Cross-Filter-State hält und Änderungen broadcastet.

    Reine Python-Klasse (kein QObject), damit auch ohne PySide6 testbar.
    Stattdessen werden Listener-Callbacks verwendet.
    """

    _instance: "CrossFilterState | None" = None

    def __init__(self) -> None:
        super().__init__()
        self.state = FilterState()
        self._listeners: list[Callable[[FilterState], None]] = []

    @classmethod
    def instance(cls) -> CrossFilterState:
        """Gibt die Singleton-Instanz zurück."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Setzt das Singleton zurück (für Tests)."""
        cls._instance = None

    def set_depot_filter(self, depot_ids: set[int]) -> None:
        """Setzt Depot-Filter und benachrichtigt Listener."""
        if self.state.depot_ids != depot_ids:
            self.state.depot_ids = set(depot_ids)
            self._notify()

    def set_praeparat_filter(self, praeparat_ids: set[int]) -> None:
        """Setzt Präparat-Filter und benachrichtigt Listener."""
        if self.state.praeparat_ids != praeparat_ids:
            self.state.praeparat_ids = set(praeparat_ids)
            self._notify()

    def set_date_range(self, days: int) -> None:
        """Setzt den globalen Zeitraum (7/30/90/365)."""
        if self.state.date_range_days != days:
            self.state.date_range_days = days
            self._notify()

    def clear_all(self) -> None:
        """Setzt alle Filter zurück."""
        self.state.clear()
        self._notify()

    def add_listener(self, callback: Callable[[FilterState], None]) -> None:
        """Registriert einen Listener, der bei Filter-Änderungen aufgerufen wird."""
        self._listeners.append(callback)

    def _notify(self) -> None:
        """Benachrichtigt alle Listener."""
        for callback in self._listeners:
            try:
                callback(self.state)
            except Exception:
                logger.exception("Cross-Filter-Listener fehlgeschlagen")
