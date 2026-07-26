"""MainWindow shell helpers (Issue #93)."""
from __future__ import annotations

import logging

from core.data_access_layer import (
    OperatingMode,
)
from PySide6 import QtCore, QtWidgets

logger = logging.getLogger("ND-Hub")

def _init_timers(self) -> None:
    """Startet Auto-Refresh-Timer"""
    self.verfall_refresh_timer = QtCore.QTimer(self)
    self.verfall_refresh_timer.timeout.connect(self.refresh_verfall_widgets)
    self.verfall_refresh_timer.start(300000)  # 5 Minuten

    self.write_lease_timer = QtCore.QTimer(self)
    self.write_lease_timer.timeout.connect(self._heartbeat_write_lease)
    self.write_lease_timer.start(10000)  # 10 Sekunden

    self.sync_timer = QtCore.QTimer(self)
    self.sync_timer.timeout.connect(self._run_sync_cycle)
    self._refresh_sync_scheduler()


def _refresh_sync_scheduler(self) -> None:
    """Aktualisiert den periodischen Sync-Timer anhand der aktuellen Konfiguration."""
    if not hasattr(self, "sync_timer"):
        return
    mode = OperatingMode.from_raw(self.config.get_operating_mode())
    interval_ms = max(10, self.config.get_sync_interval_seconds()) * 1000
    self.sync_timer.setInterval(interval_ms)
    if mode == OperatingMode.HYBRID_SYNC:
        if not self.sync_timer.isActive():
            self.sync_timer.start()
            QtCore.QTimer.singleShot(1000, self._run_sync_cycle)
        logger.info("Sync-Timer aktiv: mode=%s interval=%ss", mode.value, interval_ms // 1000)
    else:
        if self.sync_timer.isActive():
            self.sync_timer.stop()
        logger.info("Sync-Timer pausiert: mode=%s", mode.value)


def _heartbeat_write_lease(self) -> None:
    """Aktualisiert den Write-Lease periodisch."""
    if not hasattr(self, "db") or not hasattr(self, "security"):
        return
    username = self.security.get_current_user()
    if not username:
        return
    if self.db.write_lease_owner:
        still_writer = self.db.refresh_write_lease(username)
        if not still_writer:
            self.security.set_query_only(True)
            QtWidgets.QMessageBox.warning(
                self,
                "Schreibzugriff verloren",
                "Diese Sitzung wurde in den Nur-Lesen Modus versetzt.",
            )
            self.show_toast("Schreibzugriff verloren - Nur-Lesen Modus aktiv.", "warning", 3200)
            self._refresh_user_sidebar_state()
            current = self.stack.currentWidget() if hasattr(self, "stack") else None
            if current is not None:
                self._apply_write_mode_to_page(current)


def _run_sync_cycle(self) -> None:
    """Plant einen Push/Pull-Cycle im QThreadPool (non-blocking).

    Vorher lief ``self.sync_service.run_cycle`` synchron im UI-Thread
    und konnte bei langsamen Backend-Antworten die UI einfrieren.
    Mit dem Worker-Runner läuft der Cycle in einem Worker-Thread und
    die UI bleibt reaktiv. Ergebnis-Updates kommen via Signal zurück.
    """
    if not hasattr(self, "sync_worker_runner") or not hasattr(self, "security"):
        return
    username = self.security.get_current_user()
    if not username:
        return
    started = self.sync_worker_runner.submit(username)
    if not started:
        # Bereits ein Cycle aktiv oder Username leer — kein Log-Spam
        # (Timer feuert u. U. häufiger als Intervalle abgeschlossen sind).
        return


def _on_sync_cycle_finished(self, payload: dict) -> None:
    """Slot: erfolgreicher Sync-Cycle, ggf. UI aktualisieren."""
    pushed = payload.get("pushed", 0) or 0
    pulled = payload.get("pulled", 0) or 0
    rejected = payload.get("rejected", 0) or 0
    conflicts = payload.get("conflicts", 0) or 0
    if pushed or pulled or rejected or conflicts:
        logger.info(
            "Sync-Zyklus: mode=%s pushed=%s pulled=%s rejected=%s conflicts=%s reason=%s",
            payload.get("effective_mode"),
            pushed,
            pulled,
            rejected,
            conflicts,
            payload.get("reason"),
        )
    # Pull kann Stammdaten/Depots verändert haben → Cache invalidieren
    # und ggf. sichtbare Seiten neu laden.
    if pulled:
        try:
            if hasattr(self.db, "_clear_lookup_caches"):
                self.db._clear_lookup_caches()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Cache-Invalidierung nach Sync fehlgeschlagen: %s", exc)
        if hasattr(self, "_refresh_user_sidebar_state"):
            self._refresh_user_sidebar_state()


def _on_sync_cycle_failed(self, message: str) -> None:
    """Slot: Sync-Cycle fehlgeschlagen."""
    logger.warning("Sync-Zyklus fehlgeschlagen: %s", message)


def _on_sync_cycle_skipped(self, reason: str) -> None:
    """Slot: Sync-Cycle wurde übersprungen (z. B. kein Hybrid-Mode)."""
    logger.debug("Sync-Cycle übersprungen: %s", reason)

