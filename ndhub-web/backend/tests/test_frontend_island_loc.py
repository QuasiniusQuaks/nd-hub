"""Frontend island modules stay under the LOC gate (Issue #111)."""

from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend-react" / "src"


def test_frontend_tsx_under_800_loc():
    files = list(SRC.rglob("*.tsx"))
    assert files
    oversized = []
    for path in files:
        loc = len(path.read_text(encoding="utf-8").splitlines())
        if loc > 800:
            oversized.append(f"{path.relative_to(SRC)}:{loc}")
    assert oversized == []


def test_main_tsx_is_bootstrap_only():
    loc = len((SRC / "main.tsx").read_text(encoding="utf-8").splitlines())
    assert loc <= 120
