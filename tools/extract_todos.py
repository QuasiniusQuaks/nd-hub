#!/usr/bin/env python3
"""Extrahiert TODO/FIXME/XXX/HACK-Marker aus dem Quellcode.

Usage:
    python3 tools/extract_todos.py [--root ROOT] [--format {json,md}]

Ausgabe:
    - JSON: Maschinenlesbare Liste aller Treffer.
    - Markdown: Menschenlesbare Tabelle (Default).

Ignoriert bewusst:
    - `resources.py` (Base64-kodierte Assets enthalten zufällig diese Wörter).
    - Dateien unter `.git`, `__pycache__`, `node_modules`, `dist`, `build`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

MARKER_RE = re.compile(r"#\s*(TODO|FIXME|XXX|HACK)(?:\(([^)]+)\))?[:\s]?(.*)", re.IGNORECASE)
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", "dist", "build", ".venv", "venv"}
EXCLUDED_FILES = {"resources.py"}


@dataclass(frozen=True)
class TodoItem:
    marker: str
    author: str
    text: str
    file: str
    line: int


def find_source_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in filenames:
            if filename in EXCLUDED_FILES:
                continue
            if filename.endswith((".py", ".md", ".sh", ".toml", ".yaml", ".yml", ".json")):
                yield Path(dirpath) / filename


def extract_todos(root: Path) -> list[TodoItem]:
    items: list[TodoItem] = []
    for path in find_source_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = MARKER_RE.search(line)
            if match:
                marker, author, desc = match.groups()
                items.append(
                    TodoItem(
                        marker=marker.upper(),
                        author=author or "",
                        text=(desc or "").strip(),
                        file=str(path.relative_to(root)),
                        line=lineno,
                    )
                )
    return sorted(items, key=lambda i: (i.file, i.line))


def render_markdown(items: list[TodoItem]) -> str:
    lines = [
        "# Tech-Debt-Inventar",
        "",
        "| Datei | Zeile | Marker | Autor | Beschreibung |",
        "|-------|-------|--------|-------|--------------|",
    ]
    for item in items:
        author = item.author or "—"
        lines.append(
            f"| `{item.file}` | {item.line} | {item.marker} | {author} | {item.text} |"
        )
    if not items:
        lines.append("| — | — | — | — | Keine offenen Marker gefunden. |")
    lines.append("")
    lines.append(
        "_Generiert automatisch mit `tools/extract_todos.py`."
        " Bitte manuell aktualisieren, wenn Issues angelegt werden._"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrahiere TODO/FIXME/XXX/HACK Marker.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repo-Root")
    parser.add_argument(
        "--format", choices=("json", "md"), default="md", help="Ausgabeformat"
    )
    args = parser.parse_args()

    items = extract_todos(args.root.resolve())

    if args.format == "json":
        print(json.dumps([asdict(item) for item in items], indent=2))
    else:
        sys.stdout.write(render_markdown(items))

    return 0 if not items else 1


if __name__ == "__main__":
    raise SystemExit(main())
