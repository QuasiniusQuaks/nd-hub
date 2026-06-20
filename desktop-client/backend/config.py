"""Backend configuration helpers."""

from __future__ import annotations

import os


def resolve_db_path() -> str:
    """Resolve database path for backend usage."""
    env_path = os.environ.get("ND_HUB_DB_PATH", "").strip()
    if env_path:
        return env_path

    # For the first solo migration step we keep backend data local to the project
    # unless explicitly overridden via ND_HUB_DB_PATH.
    return os.path.abspath("nd_hub_backend.db")

