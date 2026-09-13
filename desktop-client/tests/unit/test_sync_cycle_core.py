"""Pure sync-cycle core without QThreadPool (Issue #117)."""

from __future__ import annotations

from dataclasses import dataclass

from core.sync_worker import execute_sync_cycle


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
    def __init__(self, raise_exc: bool = False, result: FakeCycleResult | None = None):
        self.raise_exc = raise_exc
        self.result = result or FakeCycleResult(pushed=3, pulled=2)
        self.call_count = 0
        self.last_username = None

    def run_cycle(self, actor_username: str) -> FakeCycleResult:
        self.call_count += 1
        self.last_username = actor_username
        if self.raise_exc:
            raise RuntimeError("Simulierter Sync-Fehler")
        return self.result


def test_execute_sync_cycle_finished_payload():
    service = FakeService(result=FakeCycleResult(pushed=7, pulled=4, conflicts=1))
    outcome = execute_sync_cycle(service, "alice")
    assert outcome["kind"] == "finished"
    assert outcome["payload"]["pushed"] == 7
    assert outcome["payload"]["pulled"] == 4
    assert outcome["payload"]["conflicts"] == 1
    assert service.call_count == 1
    assert service.last_username == "alice"


def test_execute_sync_cycle_skipped():
    service = FakeService(result=FakeCycleResult(skipped=True, reason="Kein Token"))
    outcome = execute_sync_cycle(service, "alice")
    assert outcome["kind"] == "skipped"
    assert outcome["reason"] == "Kein Token"


def test_execute_sync_cycle_failed():
    service = FakeService(raise_exc=True)
    outcome = execute_sync_cycle(service, "alice")
    assert outcome["kind"] == "failed"
    assert "Simulierter Sync-Fehler" in outcome["error"]
