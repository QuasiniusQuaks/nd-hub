"""Web backend test bootstrap (Issue #141)."""

from __future__ import annotations

import os


def pytest_configure(config) -> None:
    # Importing backend.app instantiates create_app() at module level.
    # First-admin is fail-closed without ND_HUB_INITIAL_ADMIN_PASSWORD.
    os.environ.setdefault(
        "ND_HUB_INITIAL_ADMIN_PASSWORD",
        "TestAdmin!conftest-not-for-prod",
    )
