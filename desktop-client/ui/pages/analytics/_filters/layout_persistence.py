"""Dashboard-Layout-Persistenz — speichert aktiven Tab + Filter als JSON.

Speichert/Lädt den Analytics-Layout-State (aktiver Tab, Zeitraum,
Cross-Filter, Vergleichs-Modus) in einer JSON-Datei im Data-Verzeichnis.

Issue #42 Phase 2 — Dashboard-Layout-Persistenz.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LayoutPersistence:
    """Speichert/Lädt den Analytics-Layout-State als JSON."""

    def __init__(self, data_dir: str = ".") -> None:
        """Initialisiert mit dem Data-Verzeichnis.

        Args:
            data_dir: Verzeichnis für die Layout-Datei.
                      Default: aktuelles Verzeichnis.
        """
        self._file_path = Path(data_dir) / "analytics_layout.json"

    @property
    def file_path(self) -> Path:
        """Pfad zur Layout-JSON-Datei."""
        return self._file_path

    def save_layout(self, state: dict) -> bool:
        """Speichert den Layout-State als JSON.

        Args:
            state: dict mit:
                - active_tab: int (0-3)
                - date_range_days: int
                - depot_ids: list[int]
                - praeparat_ids: list[int]
                - compare_mode: bool

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Layout gespeichert: %s", self._file_path)
            return True
        except Exception:
            logger.exception("Layout-Save fehlgeschlagen: %s", self._file_path)
            return False

    def load_layout(self) -> dict | None:
        """Lädt den Layout-State aus JSON.

        Returns:
            dict oder None wenn Datei nicht existiert/ladefehler.
        """
        try:
            if not self._file_path.exists():
                return None
            data = self._file_path.read_text(encoding="utf-8")
            return json.loads(data)
        except Exception:
            logger.exception("Layout-Load fehlgeschlagen: %s", self._file_path)
            return None

    def clear_layout(self) -> bool:
        """Löscht die Layout-Datei.

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            if self._file_path.exists():
                self._file_path.unlink()
            return True
        except Exception:
            logger.exception("Layout-Clear fehlgeschlagen")
            return False

    def exists(self) -> bool:
        """True wenn eine Layout-Datei existiert."""
        return self._file_path.exists()
