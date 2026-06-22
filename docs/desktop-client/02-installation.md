# Desktop Client: Installation

## Voraussetzungen

| Komponente | Version |
|---|---|
| Python | 3.10 oder 3.11 |
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
python run_notfalldepots.py
```

Beim ersten Start:

- Daten- und Konfigverzeichnis (`~/.ND-Hub` bzw. `%APPDATA%/ND-Hub`)
  wird automatisch angelegt.
- Der Setup-Wizard fuehrt durch die Erstkonfiguration.

## Entwicklungs-Tooling

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

CI-Anforderungen (Linux + Windows, Python 3.10/3.11):

- Lint und Format-Check muessen gruen sein.
- Test-Coverage mit Mindestschwelle (aktuell 30 % fuer Kernmodule).
- Security-Scan (`bandit`) und Dependency-Audit (`pip-audit`).

Performance-Tests sind separat:

- Lokal: `pytest -m performance --no-cov`
- GitHub Actions: manueller Workflow `Performance Tests`.

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
