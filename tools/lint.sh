#!/usr/bin/env bash
# tools/lint.sh — zentrales Lint-Skript für nd-hub
# Spiegelt die CI-Ruff-Gates (Workflow ci.yml, Job lint). Bei Erfolg Exit 0, sonst Exit 1.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if ! command -v ruff >/dev/null 2>&1; then
    echo "ruff nicht gefunden. Bitte installieren: pip install ruff"
    exit 1
fi

echo "==> ruff check desktop-client/"
ruff check desktop-client \
    --config desktop-client/pyproject.toml \
    --exclude "**/tests/**,**/.venv/**,**/__pycache__/**"

echo "==> ruff check ndhub-web/"
ruff check ndhub-web \
    --config ndhub-web/pyproject.toml \
    --exclude "**/tests/**,**/.venv/**,**/node_modules/**,**/__pycache__/**"

echo "==> ruff check shared/"
ruff check shared --config desktop-client/pyproject.toml

echo "==> Lint OK"
