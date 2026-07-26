"""Unit tests for pure login lockout tracker (Issue #96)."""

from __future__ import annotations

import time

from backend.login_protection import LoginLockoutTracker, LoginProtectionConfig


def test_lockout_after_max_fails():
    tracker = LoginLockoutTracker(max_fails=2, lockout_seconds=5)
    assert tracker.check("alice") is None
    assert tracker.record_failure("alice") is None
    locked = tracker.record_failure("alice")
    assert locked == 5
    remaining = tracker.check("alice")
    assert remaining is not None and remaining > 0


def test_clear_resets_counter():
    tracker = LoginLockoutTracker(max_fails=2, lockout_seconds=5)
    tracker.record_failure("bob")
    tracker.clear("bob")
    assert tracker.check("bob") is None
    assert tracker.record_failure("bob") is None  # first fail after clear


def test_lockout_expires(monkeypatch):
    tracker = LoginLockoutTracker(max_fails=1, lockout_seconds=10)
    now = 1_700_000_000.0
    monkeypatch.setattr(time, "time", lambda: now)
    assert tracker.record_failure("carol") == 10
    assert tracker.check("carol") == 10
    monkeypatch.setattr(time, "time", lambda: now + 11)
    assert tracker.check("carol") is None


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("ND_HUB_LOGIN_IP_LIMIT", "7/minute")
    monkeypatch.setenv("ND_HUB_LOGIN_MAX_FAILS", "3")
    monkeypatch.setenv("ND_HUB_LOGIN_LOCKOUT_SECONDS", "42")
    cfg = LoginProtectionConfig.from_env()
    assert cfg.ip_limit == "7/minute"
    assert cfg.max_fails == 3
    assert cfg.lockout_seconds == 42
