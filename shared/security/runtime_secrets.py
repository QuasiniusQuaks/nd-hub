"""Reject empty and example-placeholder secrets (Issues #141, #142)."""

from __future__ import annotations

import os

# Documented .env.example tokens and historical compose defaults. Compared
# case-insensitively after stripping; hyphens/spaces dropped for compact form.
PLACEHOLDER_SECRETS = frozenset(
    {
        "__change_me__",
        "changeme",
        "changerootme",
        "change_me",
        "changemetoastrongpassword_123!",
    }
)


class PlaceholderSecretError(RuntimeError):
    """Deploy secret missing or still the documented example value."""


def normalize_secret(value: str | None) -> str:
    return (value or "").strip()


def is_placeholder_secret(value: str | None) -> bool:
    text = normalize_secret(value).lower()
    if not text:
        return False
    compact = text.replace("-", "").replace(" ", "")
    return text in PLACEHOLDER_SECRETS or compact in PLACEHOLDER_SECRETS


def require_runtime_secret(
    name: str,
    value: str | None,
    *,
    allow_empty: bool = False,
) -> str:
    """Return a usable secret or raise PlaceholderSecretError.

    Empty is missing (unless allow_empty). ``__CHANGE_ME__`` and known
    historical defaults are never accepted — Compose ``:?`` only catches empty.
    """
    text = normalize_secret(value)
    if not text:
        if allow_empty:
            return ""
        raise PlaceholderSecretError(
            f"{name} must be set (empty values are not allowed)."
        )
    if is_placeholder_secret(text):
        raise PlaceholderSecretError(
            f"{name} still has the example placeholder; "
            "set a unique secret before start."
        )
    return text


def resolve_initial_admin_password(*, required: bool) -> str:
    """Read ND_HUB_INITIAL_ADMIN_PASSWORD. Never generate or log a secret."""
    return require_runtime_secret(
        "ND_HUB_INITIAL_ADMIN_PASSWORD",
        os.environ.get("ND_HUB_INITIAL_ADMIN_PASSWORD"),
        allow_empty=not required,
    )
