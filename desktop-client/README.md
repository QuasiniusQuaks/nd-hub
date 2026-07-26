# ND-Hub – Desktop Client v0.5

PySide6-Desktop-Client für die Notfalldepot-Verwaltung. Daten liegen unter
`%APPDATA%/ND-Hub` (Windows) bzw. `~/.ND-Hub` (Linux).

## Key Features

- Apple-inspiriertes UI inkl. Dark Mode
- `ConfigManager` trennt Config/Daten strikt vom Programmpfad
- `SecurityManager` (bcrypt, Account-Sperre, Passwortwechsel)
- Hybrid-Sync gegen ndhub-web (`core/sync_service`, `core/sync_worker`)
- Analytics Control Center (`ui/pages/analytics/**`)
- DB-Facade `db_manager.py` + Mixins unter `core/db/*`

## Projektstruktur (Ist)

```text
desktop-client/
├── core/                      # Infrastruktur
│   ├── config_manager.py
│   ├── error_handler.py
│   ├── secure_token_store.py
│   ├── sync_service.py / sync_worker.py
│   └── db/                    # DB-Mixins (Analytics, Sync, Setup, CRUD)
├── ui/
│   ├── pages/                 # UI-Seiten inkl. analytics/
│   └── dialogs/               # Login, Setup-Wizard-Package, …
├── backend/                   # Eingebettetes FastAPI (app_factory + helpers)
├── tests/                     # unit / integration / performance
├── security_manager.py        # Auth (Root-Level)
├── db_manager.py              # DB-Facade (<500 LOC)
├── nd_hub.py                  # Haupteinstieg
├── run_notfalldepots.py       # Alternativer Launcher
└── build_windows_exe.py
```

## Installation & Entwicklung

```bash
cd desktop-client
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest, ruff, bandit, …
```

### Lokal starten

```bash
python nd_hub.py
# alternativ:
python run_notfalldepots.py
```

### Lint / Tests (lokal)

```bash
ruff check . --config pyproject.toml
pytest tests/unit -m "not performance" --ignore=tests/unit/test_sync_worker.py
# Performance separat:
pytest -m performance --no-cov
```

### CI (GitHub Actions)

Workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) (`CI`):

| Job | Inhalt |
|---|---|
| **Ruff** | Lint `desktop-client/`, `ndhub-web/`, `shared/` |
| **Desktop unit** | pytest unit mit PySide6-Stub (ohne Display); Ignore: `test_sync_worker.py` |
| **Web API smoke** | `test_smoke.py` + `test_security_headers.py` (SQLite) |
| **Bandit** | medium+ gegen Produktionscode |

Kein Windows-Runner in Phase 1. Coverage-Fail-under gilt für Kernmodule (siehe `pyproject.toml`).
Image-Publish bleibt ein eigener Workflow (`publish-ndhub-web-image.yml`).

## Konfiguration

- **Windows**: `%APPDATA%/ND-Hub/settings.ini`
- **Linux**: `~/.ND-Hub/settings.ini`

---
© 2026 ND-Hub Enterprise Team. Alle Rechte vorbehalten.
