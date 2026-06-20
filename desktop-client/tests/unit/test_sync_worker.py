"""
Tests für Fix #1: Sync-Worker-Entkopplung vom UI-Thread.

Stellt sicher, dass:
1. ``SyncWorkerRunner.submit`` non-blocking ist.
2. ``run_cycle`` im Worker-Thread läuft, nicht im Aufrufer-Thread.
3. Signal ``cycle_finished`` im Haupt-Thread empfangen wird.
4. Überlappende Cycles abgewiesen werden.
5. Fehler im Worker als ``cycle_failed`` propagiert werden.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import pytest
from PySide6 import QtCore

from core.sync_worker import SyncWorkerRunner

# --- QApplication-Fixture (singleton für alle Tests) -----------------------

@pytest.fixture(scope="session")
def qt_app():
    """Eine QCoreApplication pro Test-Session, die im Haupt-Thread läuft."""
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtCore.QCoreApplication([])
    return app


# --- Test-Doubles ----------------------------------------------------------

@dataclass
class FakeCycleResult:
    effective_mode: str = "hybrid_sync"
    reason: str = "test"
    pushed: int = 0
    pulled: int = 0
    rejected: int = 0
    conflicts: int = 0
    skipped: bool = False


class FakeService:
    """Simuliert DesktopSyncService mit kontrollierter Latenz und Fehler-Trigger."""

    def __init__(self, latency: float = 0.05, raise_exc: bool = False,
                 result: FakeCycleResult | None = None):
        self.latency = latency
        self.raise_exc = raise_exc
        self.result = result or FakeCycleResult(pushed=3, pulled=2)
        self.call_count = 0
        self.last_thread_id = None

    def run_cycle(self, actor_username: str) -> FakeCycleResult:
        self.call_count += 1
        self.last_thread_id = threading.get_ident()
        if self.raise_exc:
            raise RuntimeError("Simulierter Sync-Fehler")
        time.sleep(self.latency)
        return self.result


# --- Helpers ---------------------------------------------------------------

def _wait_for_signal(signal, timeout_ms: int = 3000):
    """
    Blockiert, bis das Signal emittiert wurde, und gibt die emittierten
    Args zurück. Nutzt QEventLoop, damit queued Connections sicher zugestellt
    werden.
    """
    captured = []
    loop = QtCore.QEventLoop()

    def _collector(*args):
        captured.append(args)
        loop.quit()

    signal.connect(_collector)
    QtCore.QTimer.singleShot(timeout_ms, loop.quit)  # Timeout-Safety
    loop.exec()
    try:
        signal.disconnect(_collector)
    except (TypeError, RuntimeError):
        pass
    return captured


# --- Tests -----------------------------------------------------------------

def test_submit_runs_in_worker_thread(qt_app):
    """run_cycle darf nicht im Aufrufer-Thread laufen."""
    main_thread = threading.get_ident()
    service = FakeService(latency=0.05)
    runner = SyncWorkerRunner(service)
    try:
        ok = runner.submit("alice")
        assert ok is True
        _wait_for_signal(runner.signals.cycle_ended, timeout_ms=3000)
    finally:
        runner.wait_for_done(timeout_ms=2000)

    assert service.call_count == 1
    assert service.last_thread_id != main_thread, (
        "run_cycle lief im Haupt-Thread! Worker-Entkopplung fehlgeschlagen."
    )


def test_cycle_finished_signal_payload(qt_app):
    """cycle_finished wird mit dem erwarteten Payload-Dict emittiert."""
    service = FakeService(result=FakeCycleResult(pushed=7, pulled=4, conflicts=1))
    runner = SyncWorkerRunner(service)
    try:
        runner.submit("alice")
        captured = _wait_for_signal(runner.signals.cycle_finished, timeout_ms=3000)
    finally:
        runner.wait_for_done(timeout_ms=2000)

    assert len(captured) >= 1
    payload = captured[0][0]
    assert payload["pushed"] == 7
    assert payload["pulled"] == 4
    assert payload["conflicts"] == 1


def test_cycle_failed_signal_on_exception(qt_app):
    """Exception in run_cycle wird als cycle_failed-Signal propagiert."""
    service = FakeService(raise_exc=True)
    runner = SyncWorkerRunner(service)
    try:
        runner.submit("alice")
        captured = _wait_for_signal(runner.signals.cycle_failed, timeout_ms=3000)
    finally:
        runner.wait_for_done(timeout_ms=2000)

    assert len(captured) >= 1
    assert "Simulierter Sync-Fehler" in captured[0][0]


def test_skipped_cycle_emits_cycle_skipped(qt_app):
    service = FakeService(result=FakeCycleResult(skipped=True, reason="Kein Token"))
    runner = SyncWorkerRunner(service)
    try:
        runner.submit("alice")
        captured = _wait_for_signal(runner.signals.cycle_skipped, timeout_ms=3000)
    finally:
        runner.wait_for_done(timeout_ms=2000)

    assert len(captured) >= 1
    assert "Kein Token" in captured[0][0]


def test_overlapping_cycles_rejected(qt_app):
    """Ein zweiter submit() während laufendem Cycle muss abgelehnt werden."""
    service = FakeService(latency=0.4)  # 400ms Latenz
    runner = SyncWorkerRunner(service)
    try:
        ok1 = runner.submit("alice")
        assert ok1 is True

        # Während Cycle 1 läuft: Cycle 2 muss abgelehnt werden
        ok2 = runner.submit("bob")
        assert ok2 is False, "Zweiter submit() wurde nicht abgewiesen!"

        # Cycle 1 abschließen
        _wait_for_signal(runner.signals.cycle_ended, timeout_ms=3000)
        assert service.call_count == 1

        # Danach: dritter Submit muss wieder akzeptiert werden
        ok3 = runner.submit("carol")
        assert ok3 is True
        _wait_for_signal(runner.signals.cycle_ended, timeout_ms=3000)
        assert service.call_count == 2
    finally:
        runner.wait_for_done(timeout_ms=2000)


def test_empty_username_rejected(qt_app):
    service = FakeService()
    runner = SyncWorkerRunner(service)
    assert runner.submit("") is False
    assert runner.submit(None) is False
    assert service.call_count == 0


def test_is_running_flag_during_cycle(qt_app):
    """is_running() ist True während des Cycles, False danach."""
    service = FakeService(latency=0.2)
    runner = SyncWorkerRunner(service)
    try:
        assert runner.is_running() is False
        runner.submit("alice")
        # Kurz warten, bis der Worker-Thread den Flag gesetzt hat.
        time.sleep(0.05)
        assert runner.is_running() is True
        _wait_for_signal(runner.signals.cycle_ended, timeout_ms=3000)
        # Nach cycle_ended: Flag im Haupt-Thread wieder False
        assert runner.is_running() is False
    finally:
        runner.wait_for_done(timeout_ms=2000)
