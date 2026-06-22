"""
QThreadPool-basierter Sync-Worker.

Hintergrund: Vorher lief ``DesktopSyncService.run_cycle`` synchron im
UI-Thread. Bei langsamen Backend-Requests (Timeouts, Netzwerk) fror die
komplette Oberfläche für mehrere Sekunden ein.

Dieser Worker entkoppelt den Push/Pull-Zyklus vom UI-Thread:

  * Haupt-Thread ruft ``SyncWorkerRunner.submit(...)`` auf (non-blocking).
  * ``QThreadPool`` führt ``SyncWorkerRunnable.run()`` in einem Worker-Thread aus.
  * Status-Updates werden via ``SyncWorkerSignals`` an den Haupt-Thread
    zurückgesendet (Qt-Signal-Slot-Mechanismus ist thread-safe).

Concurrency-Safety:
  * ``SyncWorkerRunner.submit`` ist reentrant-safe: Wenn bereits ein Cycle
    läuft, wird der neue Aufruf abgewiesen (kein Overlap, keine DB-Lock-Spikes).
  * Die ``Database``-Klasse ist mit ``check_same_thread=False`` konfiguriert,
    d. h. SQLite-Operationen aus dem Worker-Thread heraus sind erlaubt (WAL-Modus).
  * Cache-Invalidierung läuft nach dem Worker-Cycle automatisch via Signal,
    sodass Listen-Daten, die durch den Pull verändert wurden, im UI neu geladen
    werden.

Lifecycle:
  * Der Worker hält keine starke Referenz auf den Haupt-Window-Thread, sondern
  * nur auf die Service-Instanz und die ``Database``-Instanz. Beide sind
  * thread-safe (siehe oben) und werden beim App-Shutdown sauber geschlossen.
"""
from __future__ import annotations

import logging
import traceback

from PySide6 import QtCore

logger = logging.getLogger("ND-Hub.SyncWorker")


class SyncWorkerSignals(QtCore.QObject):
    """Signals für die Sync-Worker-Kommunikation (thread-safe via Qt-Queues)."""
    # Wird nach erfolgreichem Cycle emittiert (Cycle-Ergebnis als Dict).
    cycle_finished = QtCore.Signal(object)  # dict mit {pushed, pulled, rejected, conflicts, ...}
    # Wird bei Fehlern im Cycle emittiert.
    cycle_failed = QtCore.Signal(str)  # Fehlermeldung
    # Wird emittiert, wenn der Cycle übersprungen wurde (kein Hybrid-Mode o. ä.).
    cycle_skipped = QtCore.Signal(str)  # Grund
    # Wird immer am Ende emittiert — auch bei Fehler — damit der UI-Thread den
    # "running"-Status zurücksetzen kann.
    cycle_ended = QtCore.Signal()


class SyncWorkerRunnable(QtCore.QRunnable):
    """
    Führt ``DesktopSyncService.run_cycle`` in einem Worker-Thread aus.

    Wichtig: ``QRunnable`` ist fire-and-forget; das Thread-Pool verwaltet
    die Worker-Instanzen. Status-Rückmeldung erfolgt ausschließlich über
    ``signals`` (Signal/Slot), die intern in Qt's thread-safe Queues landen.
    """

    def __init__(self, service, username: str, signals: SyncWorkerSignals):
        super().__init__()
        self.service = service
        self.username = username
        self.signals = signals
        # Auto-Delete: Thread-Pool räumt das Runnable nach run() auf.
        self.setAutoDelete(True)

    def run(self) -> None:  # noqa: D401  (Qt-API)
        try:
            cycle = self.service.run_cycle(actor_username=self.username)
        except Exception as exc:  # noqa: BLE001 — explizit broad, Fehler werden via Signal propagiert
            tb = traceback.format_exc(limit=2)
            logger.warning("Sync-Worker-Fehler: %s\n%s", exc, tb)
            try:
                self.signals.cycle_failed.emit(f"{type(exc).__name__}: {exc}")
            except Exception:
                # Signals dürfen niemals den Worker crashen lassen
                pass
            try:
                self.signals.cycle_ended.emit()
            except Exception:
                logger.exception("Sync-Worker Cleanup fehlgeschlagen")
            return

        try:
            if cycle.skipped:
                self.signals.cycle_skipped.emit(cycle.reason or "Übersprungen")
            else:
                payload = {
                    "effective_mode": cycle.effective_mode,
                    "reason": cycle.reason,
                    "pushed": cycle.pushed,
                    "pulled": cycle.pulled,
                    "rejected": cycle.rejected,
                    "conflicts": cycle.conflicts,
                }
                self.signals.cycle_finished.emit(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sync-Worker-Signal-Übermittlung fehlgeschlagen: %s", exc)
        finally:
            try:
                self.signals.cycle_ended.emit()
            except Exception:
                pass


class SyncWorkerRunner:
    """
    Verwaltet eingehende Sync-Anfragen und führt sie in einem ``QThreadPool`` aus.

    Verwendungs-Beispiel im Haupt-Window::

        self._sync_runner = SyncWorkerRunner(self.sync_service)
        self._sync_runner.signals.cycle_finished.connect(self._on_sync_cycle_finished)
        self._sync_runner.signals.cycle_failed.connect(self._on_sync_cycle_failed)
        self._sync_runner.signals.cycle_skipped.connect(self._on_sync_cycle_skipped)
        self._sync_runner.signals.cycle_ended.connect(self._on_sync_cycle_ended)

        # Statt self.sync_service.run_cycle(...) direkt:
        self._sync_runner.submit(self.security.get_current_user())
    """

    def __init__(self, service, max_threads: int = 1):
        self._service = service
        self._signals = SyncWorkerSignals()
        # Bewusst max. 1 paralleler Sync-Thread, da SQLite-Cache-Invalidierungen
        # sonst komplexer zu koordinieren sind und der Server ohnehin nur einen
        # Push-Endpoint hat. Für mehrere Worker: einfach den Parameter erhöhen.
        self._pool = QtCore.QThreadPool()
        self._pool.setMaxThreadCount(max(1, int(max_threads)))
        # Lock verhindert überlappende Cycles (Timer kann feuern, während
        # ein vorheriger Cycle noch läuft).
        self._active_lock = QtCore.QMutex()
        self._is_active = False

    @property
    def signals(self) -> SyncWorkerSignals:
        return self._signals

    def is_running(self) -> bool:
        return self._is_active

    def submit(self, username: str | None) -> bool:
        """
        Reicht einen Sync-Cycle im Thread-Pool ein.

        Returns ``True``, wenn der Cycle gestartet wurde; ``False``, wenn
        bereits ein anderer Cycle läuft oder der Username fehlt.
        """
        if not username:
            return False

        locker = QtCore.QMutexLocker(self._active_lock)
        if self._is_active:
            logger.debug("Sync-Worker ignoriert submit — Cycle läuft bereits.")
            return False
        self._is_active = True
        locker.unlock()

        runnable = SyncWorkerRunnable(self._service, username, self._signals)
        # Wenn der Worker endet, setzen wir _is_active zurück. Das geschieht
        # via cycle_ended-Signal, das vom Worker-Thread emittiert und im
        # Haupt-Thread-Context ausgewertet wird (queued connection).
        self._signals.cycle_ended.connect(self._on_cycle_ended)
        self._pool.start(runnable)
        return True

    def _on_cycle_ended(self) -> None:
        """Slot: wird im Haupt-Thread aufgerufen, wenn ein Cycle endet."""
        locker = QtCore.QMutexLocker(self._active_lock)
        self._is_active = False
        locker.unlock()
        try:
            self._signals.cycle_ended.disconnect(self._on_cycle_ended)
        except (TypeError, RuntimeError):
            # Mehrmaliges Disconnect ist OK, aber wenn das Signal schon weg
            # ist, ignorieren wir das.
            pass

    def wait_for_done(self, timeout_ms: int = -1) -> bool:
        """Blockiert (mit Timeout) bis alle Worker fertig sind — nur für Tests/Shutdown."""
        return self._pool.waitForDone(timeout_ms)
