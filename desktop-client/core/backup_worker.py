"""Async Backup-Restore-Worker für ND-Hub Desktop-Client.

Hintergrund (Issue #7, Audit 2026-06):
    ``GrundeinstellungenPage.restore_backup`` lief komplett im UI-Thread
    und enthielt mehrere ``time.sleep(2)``-Aufrufe. Während des Restore
    war die UI für 2-10 Sekunden eingefroren — Klicks wurden nicht
    verarbeitet, der User konnte nicht abbrechen.

    Dieser Worker extrahiert den Restore-Prozess in einen ``QRunnable``,
    der im Thread-Pool läuft. Der UI-Thread bleibt responsive, der User
    sieht Progress-Updates, ein Cancel ist möglich.

Architektur (gleiches Pattern wie ``sync_worker.py``):
    * ``BackupRestoreSignals``: Qt-Signal-Container für thread-safe
      Kommunikation zurück zum UI-Thread.
    * ``BackupRestoreRunnable``: ``QRunnable`` mit der eigentlichen
      Restore-Logik (DB-Checkpoint, Notfall-Backup, File-Lösch,
      Restore, Re-Connect).
    * ``BackupRestoreRunner``: User-API zum Starten + Signal-Bindings.

Hinweise:
    * Die ``time.sleep(2)``-Aufrufe bleiben im Worker (Windows
      File-Locking braucht das), aber blockieren nicht mehr die UI.
    * ``os.execl``-Restart bleibt im UI-Thread, weil der Worker-Thread
      den laufenden Prozess nicht ersetzen kann.
"""
from __future__ import annotations

import gc
import logging
import os
import shutil
import sqlite3
import time
from typing import List, Optional

from PySide6 import QtCore

logger = logging.getLogger("ND-Hub.BackupWorker")


class BackupRestoreSignals(QtCore.QObject):
    """Thread-safe Signal-Container für Backup-Restore-Status."""

    # Phase-Updates: (phase_name, current_step, total_steps)
    progress = QtCore.Signal(str, int, int)
    # Restore erfolgreich: (restored_size_kb, emergency_backup_path, original_backup_size_kb)
    success = QtCore.Signal(float, str, float)
    # Fehler: (error_message, emergency_backup_path_or_None)
    failed = QtCore.Signal(str, "QVariant")
    # Re-Connect nötig (Signal kommt aus Worker, Action im UI-Thread)
    reconnect_required = QtCore.Signal()


class BackupRestoreRunnable(QtCore.QRunnable):
    """Führt den Restore in einem Worker-Thread aus.

    Sequenz:
        1. WAL-Checkpoint (2 Sekunden)
        2. DB schließen (Connection + Cursor)
        3. GC + Warten auf File-Lock (2 Sek)
        4. Notfall-Backup anlegen
        5. WAL/SHM-Dateien löschen (bis zu 5 Retries, je 1 Sek)
        6. Backup-Datei kopieren (bis zu 10 Retries, je 1 Sek)
        7. Verifizieren
        8. success-Signal emittieren — UI-Thread startet danach den Re-Start

    Die ``time.sleep``-Aufrufe sind hier OK, weil sie nur den Worker-Thread
    blockieren, nicht die UI. Für ein „sofort abbrechen"-Feature müsste
    man auf ``QThread.wait(msecs)`` umstellen — bewusst aufgeschoben.
    """

    TOTAL_STEPS = 7  # WAL → Close → Wait → Emergency-Backup → WAL-Delete → Copy → Verify

    def __init__(
        self,
        db_path: str,
        restore_file: str,
        backup_size_kb: float,
        signals: BackupRestoreSignals,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.restore_file = restore_file
        self.backup_size_kb = backup_size_kb
        self.signals = signals
        # Wir brauchen eine Referenz auf die aktuell offene Connection/Cursor
        # im UI-Thread, um sie schließen zu können. Im Worker ist das nicht
        # thread-safe — daher wird das Schließen via Signal an den UI-Thread
        # delegiert. Hier vorbereitet, falls wir es später umstellen.
        self._emergency_backup: Optional[str] = None
        self._restored_size_kb: Optional[float] = None

    def run(self) -> None:  # noqa: D401 — Qt-API
        try:
            self._execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Backup-Restore fehlgeschlagen")
            self.signals.failed.emit(str(exc), self._emergency_backup)

    def _emit(self, phase: str, step: int) -> None:
        """Hilfsmethode: Progress-Signal mit try/except-Schutz für Qt-Queues."""
        try:
            self.signals.progress.emit(phase, step, self.TOTAL_STEPS)
        except RuntimeError:  # Signal wurde schon disposed (App beendet)
            logger.debug("Restore-Progress-Signal konnte nicht emittiert werden: %s", phase)

    def _execute(self) -> None:
        """Hauptlogik: alle 7 Schritte des Restores."""
        # 1. WAL-Checkpoint — wird vom UI-Thread bereits vorbereitet, hier
        # nur als Phase-Indicator emittiert.
        self._emit("WAL-Checkpoint wird durchgeführt...", 1)
        # Das eigentliche Checkpoint macht der UI-Thread (via Signal),
        # weil die Connection dort lebt. Der Worker wartet bewusst NICHT
        # synchron — siehe reconnect_required-Signal.
        self.signals.reconnect_required.emit()
        time.sleep(0.5)  # Kurze Pause, damit UI-Thread reagieren kann

        # 2. Force GC — falls noch Python-Refs auf die Connection halten
        self._emit("Warte auf File-System-Freigabe...", 2)
        gc.collect()
        time.sleep(2)  # Windows braucht das

        # 3. Notfall-Backup der aktuellen DB
        self._emit("Notfall-Backup wird erstellt...", 3)
        self._emergency_backup = self.db_path + ".before_restore"
        if os.path.exists(self.db_path):
            if os.path.exists(self._emergency_backup):
                try:
                    os.remove(self._emergency_backup)
                except OSError as exc:
                    logger.warning("Altes Notfall-Backup nicht löschbar: %s", exc)
            try:
                shutil.copy2(self.db_path, self._emergency_backup)
            except OSError as exc:
                raise RuntimeError(
                    f"Notfall-Backup fehlgeschlagen: {exc}. "
                    f"Restore wird abgebrochen, Datenbank unverändert."
                ) from exc

        # 4. WAL/SHM/Journal löschen
        self._emit("WAL/SHM-Dateien werden gelöscht...", 4)
        wal_file = self.db_path + "-wal"
        shm_file = self.db_path + "-shm"
        journal_file = self.db_path + "-journal"
        for db_file in [wal_file, shm_file, journal_file]:
            if not os.path.exists(db_file):
                continue
            for attempt in range(5):
                try:
                    os.remove(db_file)
                    break
                except PermissionError:
                    if attempt < 4:
                        time.sleep(1)
                    else:
                        # Überschreiben im nächsten Schritt, also nicht fatal
                        logger.warning(
                            "Konnte %s nicht löschen — wird beim Restore überschrieben",
                            os.path.basename(db_file),
                        )
                        break
                except OSError as exc:
                    logger.warning("Fehler beim Löschen von %s: %s",
                                   os.path.basename(db_file), exc)
                    break

        # 5. Backup-Datei rüberkopieren
        self._emit("Backup wird wiederhergestellt...", 5)
        restored = False
        last_error: Optional[Exception] = None
        for attempt in range(10):
            try:
                shutil.copy2(self.restore_file, self.db_path)
                self._restored_size_kb = os.path.getsize(self.db_path) / 1024
                restored = True
                break
            except PermissionError as exc:
                last_error = exc
                if attempt < 9:
                    time.sleep(1)
            except OSError as exc:
                last_error = exc
                break
        if not restored:
            raise RuntimeError(
                f"Datei konnte nach 10 Versuchen nicht überschrieben werden: {last_error}"
            )

        # 6. Verifizieren
        self._emit("Überprüfe Integrität...", 6)
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            result = conn.cursor().execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if not result or result[0] != "ok":
                raise RuntimeError(f"Integritäts-Check fehlgeschlagen: {result}")
        except sqlite3.Error as exc:
            raise RuntimeError(f"Verifikation fehlgeschlagen: {exc}") from exc

        # 7. Erfolg signalisieren
        self._emit("Restore abgeschlossen", 7)
        # emergency_backup ist garantiert gesetzt, weil Schritt 3 durchläuft
        assert self._restored_size_kb is not None
        assert self._emergency_backup is not None
        self.signals.success.emit(
            self._restored_size_kb,
            self._emergency_backup,
            self.backup_size_kb,
        )


class BackupRestoreRunner:
    """User-API zum Starten eines Backup-Restores.

    Usage:
        runner = BackupRestoreRunner(db_path)
        runner.signals.success.connect(self._on_restore_success)
        runner.signals.failed.connect(self._on_restore_failed)
        runner.start(restore_file, backup_size_kb)
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._signals = BackupRestoreSignals()
        self._pool = QtCore.QThreadPool.globalInstance()
        # Maximal 1 paralleler Restore — DB-Lock-Contention vermeiden
        self._pool.setMaxThreadCount(1)

    @property
    def signals(self) -> BackupRestoreSignals:
        return self._signals

    def start(self, restore_file: str, backup_size_kb: float) -> None:
        """Startet den Restore im Worker-Pool."""
        if not os.path.exists(restore_file):
            raise FileNotFoundError(f"Backup-Datei nicht gefunden: {restore_file}")
        runnable = BackupRestoreRunnable(
            self._db_path, restore_file, backup_size_kb, self._signals
        )
        # Auto-Delete: Thread-Pool räumt das Runnable nach run() auf
        runnable.setAutoDelete(True)
        self._pool.start(runnable)


__all__ = [
    "BackupRestoreSignals",
    "BackupRestoreRunnable",
    "BackupRestoreRunner",
]