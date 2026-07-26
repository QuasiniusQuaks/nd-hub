# Desktop Client: Installation

## Voraussetzungen

| Komponente | Version |
|---|---|
| Python | 3.10+ (CI: 3.12 Linux) |
| Betriebssystem | Windows 10/11, Linux (x86_64), macOS (best effort) |
| Festplatte | mind. 500 MB |
| RAM | mind. 4 GB empfohlen |

Optional fuer den Hybrid-Modus:

- erreichbares ND-Hub Web-Backend (`http://...:8000`).
- Token mit Sync-Berechtigung.

## Schnellinstallation aus dem Quellcode

```bash
cd desktop-client
python -m venv .venv
. .venv/bin/activate            # Linux/macOS
# .\.venv\Scripts\activate     # Windows
pip install -r requirements.txt
python nd_hub.py
# alternativ:
python run_notfalldepots.py
```

Beim ersten Start:

- Daten- und Konfigverzeichnis (`~/.ND-Hub` bzw. `%APPDATA%/ND-Hub`)
  wird automatisch angelegt.
- Der Setup-Wizard fuehrt durch die Erstkonfiguration.

## Entwicklungs-Tooling

```bash
pip install -r requirements-dev.txt
ruff check . --config pyproject.toml
pytest tests/unit -m "not performance" --ignore=tests/unit/test_sync_worker.py
```

### CI (GitHub Actions)

Workflow **CI** (`.github/workflows/ci.yml`), Linux / Python 3.12:

- Ruff fuer `desktop-client/`, `ndhub-web/`, `shared/`
- Desktop-Unit mit PySide6-Stub (ohne Display); dokumentierter Ignore: `test_sync_worker.py`
- Web-API-Smoke + Security-Headers (SQLite)
- Bandit medium+ (Root-`.bandit.yml`)
- Coverage-Fail-under fuer Desktop-Kernmodule (siehe `pyproject.toml`)

Kein Windows-Runner und kein `pip-audit`-Hard-Gate in Phase 1.
Image-Publish ist ein separater Workflow.

Performance-Tests sind separat und **lokal**:

```bash
pytest -m performance --no-cov
```

(Der fruehere manuelle Workflow-Name „Performance Tests“ existiert nicht;
siehe [Performance-Tests](../quality/03-performance-tests.md).)

## Windows-Installer

Fuer den klassischen Endkundenkanal wird der Desktop Client als
Windows-Installer ausgeliefert:

1. PyInstaller-Build (`build_windows_exe.py`) erzeugt `dist/ND-Hub/`.
2. Inno Setup kompiliert anschliessend `setup_nd-hub-V05.iss` zum Installer.

Mehr Details siehe [Build & Distribution](06-build-and-distribution.md).

## Linux-Hinweise

- Auf manchen Linux-Distributionen ist die Accessibility-Bridge laut.
  Das Startskript setzt automatisch `NO_AT_BRIDGE=1`.
- `run_notfalldepots.py` aktiviert eine vorhandene `.venv/` automatisch.
