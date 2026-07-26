"""Shared security primitives for Desktop + Web (Issue #94)."""

from shared.security.password import HAS_BCRYPT, hash_password, verify_password

__all__ = ["HAS_BCRYPT", "hash_password", "verify_password"]
