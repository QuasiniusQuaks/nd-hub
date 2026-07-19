"""Gemeinsame DB-Helper (Issue #66)."""
from __future__ import annotations

from typing import Any

_MISSING = object()


def _coerce_opt_float(v: Any) -> Any:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
