"""Build context must not include secrets or local DBs (Issue #105)."""

from __future__ import annotations

from pathlib import Path

NDHUB_WEB = Path(__file__).resolve().parents[2]
DOCKERIGNORE = NDHUB_WEB / ".dockerignore"


def _patterns() -> list[str]:
    lines = []
    for raw in DOCKERIGNORE.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def test_dockerignore_excludes_env_and_db_files():
    patterns = _patterns()
    assert ".env" in patterns
    assert ".env.*" in patterns
    assert "!.env.example" in patterns
    assert "*.db" in patterns
    assert "*.sqlite*" in patterns
    assert "frontend-react/node_modules" in patterns


def test_dockerignore_keeps_env_example_exception_after_env_glob():
    patterns = _patterns()
    assert patterns.index(".env.*") < patterns.index("!.env.example")
