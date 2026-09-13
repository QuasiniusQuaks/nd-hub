"""Web requirements must not pull a desktop GUI stack (Issue #107)."""

from __future__ import annotations

from pathlib import Path

REQ = Path(__file__).resolve().parents[2] / "requirements.txt"
FORBIDDEN = ("pyside6", "matplotlib", "pywin32")


def test_web_requirements_exclude_gui_stack():
    names = []
    for raw in REQ.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip().lower()
        if not line:
            continue
        names.append(line.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0].split(";", 1)[0].strip())
    for pkg in FORBIDDEN:
        assert pkg not in names
