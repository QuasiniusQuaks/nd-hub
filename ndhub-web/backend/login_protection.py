"""Login rate-limit / per-username lockout helpers (Issue #96 / #32)."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoginProtectionConfig:
    """ENV-backed login protection settings."""

    ip_limit: str = "5/minute"
    max_fails: int = 10
    lockout_seconds: int = 900

    @classmethod
    def from_env(cls) -> LoginProtectionConfig:
        return cls(
            ip_limit=os.environ.get("ND_HUB_LOGIN_IP_LIMIT", "5/minute"),
            max_fails=int(os.environ.get("ND_HUB_LOGIN_MAX_FAILS", "10")),
            lockout_seconds=int(os.environ.get("ND_HUB_LOGIN_LOCKOUT_SECONDS", "900")),
        )


class LoginLockoutTracker:
    """Thread-safe in-memory per-username lockout tracker (single-instance).

    State map: username -> (fails, lockout_until_epoch).
    Entries with lockout_until == +inf are pure failure counters.
    """

    def __init__(self, max_fails: int, lockout_seconds: int) -> None:
        self.max_fails = int(max_fails)
        self.lockout_seconds = int(lockout_seconds)
        self._state: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def check(self, username: str) -> int | None:
        """Return remaining lockout seconds if locked; otherwise None."""
        with self._lock:
            entry = self._state.get(username)
            if not entry:
                return None
            fails, lockout_until = entry
            del fails  # unused; kept for tuple shape parity
            if lockout_until == float("inf"):
                return None
            now = time.time()
            if lockout_until > now:
                return int(lockout_until - now)
            self._state.pop(username, None)
            return None

    def record_failure(self, username: str) -> int | None:
        """Record a failed attempt. Return lockout seconds if newly locked."""
        with self._lock:
            entry = self._state.get(username)
            if entry is None:
                fails, lockout_until = 0, 0.0
            else:
                fails, lockout_until = entry
            fails += 1
            if fails >= self.max_fails:
                lockout_until = time.time() + self.lockout_seconds
                self._state[username] = (fails, lockout_until)
                return self.lockout_seconds
            self._state[username] = (fails, float("inf"))
            return None

    def clear(self, username: str) -> None:
        with self._lock:
            self._state.pop(username, None)

    # Compatibility surface used by tests / app.state
    @property
    def state(self) -> dict[str, tuple[int, float]]:
        return self._state

    @property
    def lock(self) -> threading.Lock:
        return self._lock


def attach_login_protection(app: Any, config: LoginProtectionConfig | None = None) -> LoginLockoutTracker:
    """Wire slowapi limiter + lockout tracker onto app.state; register 429 handler."""
    cfg = config or LoginProtectionConfig.from_env()
    login_limiter = Limiter(key_func=get_remote_address, default_limits=[cfg.ip_limit])
    tracker = LoginLockoutTracker(max_fails=cfg.max_fails, lockout_seconds=cfg.lockout_seconds)

    app.state.login_limiter = login_limiter
    app.state.login_lockout_state = tracker.state
    app.state.login_lockout_lock = tracker.lock
    app.state.login_max_fails = cfg.max_fails
    app.state.login_lockout_seconds = cfg.lockout_seconds
    app.state.login_lockout_tracker = tracker
    app.state.login_ip_limit = cfg.ip_limit

    async def _rate_limit_handler(_request: StarletteRequest, exc: RateLimitExceeded):
        retry_after = 60
        try:
            if hasattr(exc, "limit") and exc.limit and hasattr(exc.limit, "seconds"):
                retry_after = exc.limit.seconds
        except Exception:
            logger.exception("Unexpected error resolving rate-limit retry-after")
        return JSONResponse(
            status_code=429,
            content={"detail": f"Zu viele Login-Versuche. Bitte {retry_after}s warten."},
            headers={"Retry-After": str(retry_after)},
        )

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    return tracker


def audit_login_lockout(
    security: Any,
    *,
    username: str,
    ip: str,
    max_fails: int,
    lockout_seconds: int,
) -> None:
    """Best-effort audit log entry when a lockout is triggered."""
    try:
        security.log_activity(
            user_id=0,
            username=username,
            action="login_lockout",
            details=f"ip={ip} max_fails={max_fails} lockout_seconds={lockout_seconds}",
            ip=ip,
        )
    except Exception:
        logger.warning("Audit-Log fuer login_lockout fehlgeschlagen", exc_info=True)


def make_login_lockout_callbacks(
    tracker: LoginLockoutTracker,
    security: Any,
    *,
    max_fails: int,
    lockout_seconds: int,
) -> tuple[Callable[[str], int | None], Callable[[str], int | None], Callable[[str], None], Callable[[str, str], None]]:
    """Return (_check, _record, _clear, _audit) matching prior factory closures."""

    def _check(username: str) -> int | None:
        return tracker.check(username)

    def _record(username: str) -> int | None:
        return tracker.record_failure(username)

    def _clear(username: str) -> None:
        tracker.clear(username)

    def _audit(username: str, ip: str) -> None:
        audit_login_lockout(
            security,
            username=username,
            ip=ip,
            max_fails=max_fails,
            lockout_seconds=lockout_seconds,
        )

    return _check, _record, _clear, _audit
