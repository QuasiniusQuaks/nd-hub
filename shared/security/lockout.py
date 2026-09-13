"""Canonical login lockout policy (Issue #112)."""

from __future__ import annotations

from datetime import datetime, timedelta

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
LOCK_TS_FMT = "%Y-%m-%d %H:%M:%S"


def parse_lock_time(locked_until: str | None) -> datetime | None:
    if not locked_until:
        return None
    return datetime.strptime(str(locked_until), LOCK_TS_FMT)


def is_currently_locked(locked_until: str | None, *, now: datetime | None = None) -> bool:
    lock_time = parse_lock_time(locked_until)
    if lock_time is None:
        return False
    return (now or datetime.now()) < lock_time


def register_failed_attempt(
    failed_attempts: int,
    *,
    now: datetime | None = None,
) -> tuple[int, str | None, str]:
    """Return (new_count, locked_until or None, user message)."""
    count = int(failed_attempts) + 1
    current = now or datetime.now()
    if count >= MAX_FAILED_ATTEMPTS:
        locked_until = (current + timedelta(minutes=LOCKOUT_MINUTES)).strftime(LOCK_TS_FMT)
        message = (
            f"Account wurde nach {MAX_FAILED_ATTEMPTS} Fehlversuchen "
            f"für {LOCKOUT_MINUTES} Minuten gesperrt"
        )
        return count, locked_until, message
    remaining = MAX_FAILED_ATTEMPTS - count
    return count, None, f"Falsches Passwort ({remaining} Versuche übrig)"
