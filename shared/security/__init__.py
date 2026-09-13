"""Shared security primitives for Desktop + Web (Issue #94)."""

from shared.security.lockout import (
    MAX_FAILED_ATTEMPTS,
    is_currently_locked,
    register_failed_attempt,
)
from shared.security.password import HAS_BCRYPT, hash_password, verify_password

__all__ = [
    "HAS_BCRYPT",
    "MAX_FAILED_ATTEMPTS",
    "hash_password",
    "is_currently_locked",
    "register_failed_attempt",
    "verify_password",
]
