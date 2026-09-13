"""Frontend image/CI must match Vite engines (Issues #138 #139 #140)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = ROOT / "ndhub-web" / "Dockerfile"
CI = ROOT / ".github" / "workflows" / "ci.yml"
LOCK = ROOT / "ndhub-web" / "frontend-react" / "package-lock.json"
PKG = ROOT / "ndhub-web" / "frontend-react" / "package.json"


def _dockerfile_node() -> tuple[int, int]:
    text = DOCKERFILE.read_text(encoding="utf-8")
    match = re.search(r"^FROM\s+node:(\d+)\.(\d+)", text, re.MULTILINE)
    assert match, "Dockerfile frontend stage must pin node:MAJOR.MINOR"
    return int(match.group(1)), int(match.group(2))


def _vite_node_ok(major: int, minor: int) -> bool:
    # vite@8 engines: ^20.19.0 || >=22.12.0
    if major == 20:
        return minor >= 19
    if major == 22:
        return minor >= 12
    return major > 22


def test_dockerfile_node_satisfies_vite_8_engines():
    major, minor = _dockerfile_node()
    assert _vite_node_ok(major, minor), (
        f"Dockerfile node:{major}.{minor} is below Vite 8 engines "
        "(need ^20.19 or >=22.12); GHCR publish breaks on npm run build"
    )


def test_ci_frontend_build_job_is_a_success_gate():
    text = CI.read_text(encoding="utf-8")
    assert "npm ci" in text
    assert "npm run build" in text
    assert "ndhub-web/frontend-react" in text
    success = text.split("ci-success:", 1)[-1]
    assert "frontend-build" in success or "Frontend build" in success
    needs_line = re.search(r"needs:\s*\[([^\]]+)\]", success)
    assert needs_line, "ci-success must declare needs"
    needed = needs_line.group(1)
    assert "frontend-build" in needed


def test_lockfile_overrides_nanoid_and_postcss_advisories():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    packages = lock.get("packages") or {}
    nanoid = packages.get("node_modules/nanoid") or {}
    postcss = packages.get("node_modules/postcss") or {}
    nanoid_ver = tuple(int(p) for p in str(nanoid.get("version", "0.0.0")).split(".")[:3])
    postcss_ver = tuple(int(p) for p in str(postcss.get("version", "0.0.0")).split(".")[:3])
    assert nanoid_ver >= (3, 3, 18), nanoid
    assert postcss_ver >= (8, 5, 23), postcss
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    overrides = pkg.get("overrides") or {}
    assert "nanoid" in overrides
    assert "postcss" in overrides
