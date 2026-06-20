#!/usr/bin/env bash
# tools/lint.sh — zentrales Lint-Skript für nd-hub
# Verwendet ruff. Bei Erfolg Exit 0, sonst Exit 1.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if ! command -v ruff >/dev/null 2>&1; then
    echo "ruff nicht gefunden. Bitte installieren: pip install ruff"
    exit 1
fi

echo "==> ruff check desktop-client/ ndhub-web/"
ruff check desktop-client/ ndhub-web/

echo "==> Lint OK"
