# -*- coding: utf-8 -*-
"""Async Auth-Worker fuer ND-Hub Desktop-Client.

Hintergrund (Issue #33, Audit 2026-06):
    ``PasswordDialog.check_password`` und andere Login-Fluesse fuehren die
    Passwort-Verifikation (PBKDF2 mit 600k Iterationen) direkt im UI-Thread
    aus. Das blockiert die GUI fuer ~100-300ms, ermoeglicht kein Cancel und
    fuehlt sich bei langsamen CPUs deutlich laenger an.

    Dieser Worker extrahiert ``SecurityManager.verify_password`` in einen
    ``QRunnable``, der im Thread-Pool laeuft. Der UI-Thread bleibt responsive,
    ein Cancel ist moeglich, und das Ergebnis kommt thread-safe per Signal
    zurueck.

Architektur (gleiches Pattern wie ``backup_worker.py``):
    * ``AuthVerifySignals``: Qt-Signal-Container fuer thread-safe
      Kommunikation zurueck zum UI-Thread.
    * ``AuthVerifyRunnable``: ``QRunnable`` mit der eigentlichen
      Verifikations-Logik.
    * ``AuthVerifyRunner``: User-API zum Starten + Signal-Bindings.

Hinweise:
    * Der Worker benoetigt den Hash zum Zeitpunkt des Starts. Der Aufrufer
      ist dafuer verantwortlich, den Hash im UI-Thread zu laden.
    * ``verify_password`` ist als reine CPU-Operation thread-safe (keine
      Shared State), solange ``SecurityManager`` keine Instanzvariablen
      nutzt — was fuer die statische Methode zutrifft.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6 import QtCore

logger = logging.getLogger("ND-Hub.AuthWorker")


class AuthVerifySignals(QtCore.QObject):
    """Thread-safe Signal-Container fuer Auth-Verifikations-Status."""

    # (is_valid: bool)
    finished = QtCore.Signal(bool)
    # (error_message: str)
    failed = QtCore.Signal(str)


class AuthVerifyRunnable(QtCore.QRunnable):
    """Fuehrt die Passwort-Verifikation in einem Worker-Thread aus."""

    def __init__(
        self,
        password: str,
        password_hash: str,
        signals: AuthVerifySignals,
    ) -> None:
        super().__init__()
        self.password = password
        self.password_hash = password_hash
        self.signals = signals

    def run(self) -> None:  # noqa: D401 — Qt-API
        is_valid, error_message = _verify_password(self.password, self.password_hash)
        if error_message is not None:
            self.signals.failed.emit(error_message)
        else:
            self.signals.finished.emit(is_valid)


def _verify_password(password: str, password_hash: str) -> tuple[bool, Optional[str]]:
    """Pure-Python-Hilfsfunktion fuer Tests.

    Returns:
        (is_valid, error_message). ``error_message`` ist ``None``, wenn die
        Verifikation ohne Fehler durchlief (egal ob True oder False).
    """
    try:
        from security_manager import SecurityManager

        is_valid = SecurityManager.verify_password(password, password_hash)
        return is_valid, None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Auth-Verifikation fehlgeschlagen")
        return False, str(exc)


class AuthVerifyRunner:
    """User-API zum Starten einer asynchronen Passwort-Verifikation.

    Usage:
        runner = AuthVerifyRunner()
        runner.signals.finished.connect(self._on_auth_finished)
        runner.signals.failed.connect(self._on_auth_failed)
        runner.start(password, password_hash)
    """

    def __init__(self) -> None:
        self._signals = AuthVerifySignals()
        self._pool = QtCore.QThreadPool.globalInstance()

    @property
    def signals(self) -> AuthVerifySignals:
        return self._signals

    def start(self, password: str, password_hash: str) -> None:
        """Startet die Verifikation im Worker-Pool."""
        runnable = AuthVerifyRunnable(password, password_hash, self._signals)
        runnable.setAutoDelete(True)
        self._pool.start(runnable)


__all__ = [
    "AuthVerifySignals",
    "AuthVerifyRunnable",
    "AuthVerifyRunner",
]
