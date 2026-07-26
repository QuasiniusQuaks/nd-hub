"""Canonical password hashing / verification (Issue #94).

Used by both desktop-client and ndhub-web ``SecurityManager`` adapters.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)

try:
    import bcrypt

    HAS_BCRYPT = True
except ImportError:  # pragma: no cover
    bcrypt = None  # type: ignore[assignment]
    HAS_BCRYPT = False

PBKDF2_ITERATIONS_MODERN = 600_000
PBKDF2_ITERATIONS_LEGACY = 100_000


def hash_password(password: str) -> str:
    """Hash a password (bcrypt if available, else PBKDF2-HMAC-SHA256)."""
    if HAS_BCRYPT:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS_MODERN
    )
    return salt.hex() + pwdhash.hex()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash with constant-time PBKDF2 compares.

    Both modern (600k) and legacy (100k) PBKDF2 variants are always computed
    so timing does not leak the hash format (Fix #29).
    """
    if not password_hash:
        return False
    try:
        if HAS_BCRYPT and password_hash.startswith("$2"):
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        salt = bytes.fromhex(password_hash[:64])
        password_bytes = password.encode("utf-8")
        modern = hashlib.pbkdf2_hmac(
            "sha256", password_bytes, salt, PBKDF2_ITERATIONS_MODERN
        ).hex()
        legacy = hashlib.pbkdf2_hmac(
            "sha256", password_bytes, salt, PBKDF2_ITERATIONS_LEGACY
        ).hex()
        modern_match = hmac.compare_digest(modern, password_hash[64:])
        legacy_match = hmac.compare_digest(legacy, password_hash[64:])
        return modern_match or legacy_match
    except Exception as exc:
        logger.error("Passwort-Verifikation fehlgeschlagen: %s", exc)
        return False
