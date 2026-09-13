"""Shared lockout policy (Issue #112)."""

from __future__ import annotations

from datetime import datetime, timedelta

from shared.security.lockout import (
    LOCKOUT_MINUTES,
    MAX_FAILED_ATTEMPTS,
    is_currently_locked,
    register_failed_attempt,
)


def test_register_failed_attempt_locks_on_threshold():
    now = datetime(2026, 1, 1, 12, 0, 0)
    count, locked, msg = register_failed_attempt(MAX_FAILED_ATTEMPTS - 1, now=now)
    assert count == MAX_FAILED_ATTEMPTS
    assert locked == (now + timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    assert "gesperrt" in msg


def test_register_failed_attempt_keeps_remaining_tries():
    count, locked, msg = register_failed_attempt(0)
    assert count == 1
    assert locked is None
    assert "4 Versuche" in msg


def test_is_currently_locked():
    now = datetime(2026, 1, 1, 12, 0, 0)
    future = (now + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    past = (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    assert is_currently_locked(future, now=now) is True
    assert is_currently_locked(past, now=now) is False
    assert is_currently_locked(None, now=now) is False
