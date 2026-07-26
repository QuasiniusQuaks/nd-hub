# Webanwendung: Backend

Das Backend ist eine FastAPI-Anwendung. Einstieg ist ein duenner Shim
`backend/app.py`; die eigentliche App entsteht in `backend/app_factory.py`
(`create_app`), der Domain-Router aus `shared/routers/*` und web-only Router
einbindet.

## Stack

| Komponente | Version |
|---|---|
| Python | 3.12 (im Container) |
| FastAPI | >= 0.116 |
| uvicorn | >= 0.35 |
| pandas | >= 2.2 |
| openpyxl | >= 3.1 |
| reportlab | >= 4.2 |
| python-pptx | >= 1.0 |
| bcrypt | >= 4.1 |
| PyMySQL | >= 1.1 |

Vollstaendige Liste: `ndhub-web/requirements.txt`.

## Start

```bash
cd ndhub-web
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python run_backend.py
```

Standardwerte:

- Host: `127.0.0.1` (`ND_HUB_BACKEND_HOST`)
- Port: `8000` (`ND_HUB_BACKEND_PORT`)

Oder containerisiert via [Deployment / Docker-Stack](../deployment/01-docker-stack.md).

## Modulueberblick

| Modul | Zweck |
|---|---|
| `backend/app.py` | Shim: re-export / `create_app`-Aufruf. |
| `backend/app_factory.py` | Lifecycle, Middleware, Router-Mount, Wiring. |
| `backend/helpers.py` | Imports, Backup-Hilfen, Report-Helfer. |
| `backend/auth.py` | Token-Store, Login/Refresh, Permissions. |
| `backend/database.py` | `SqliteRepository`, Schemaverwaltung. |
| `backend/mariadb_repository.py` | `MariaDbRepository` mit optionalem Dual-Write. |
| `backend/config.py` | Resolver fuer Engine, Pfade, SMTP. |
| `shared/routers/*` | Domain-REST (auth, users, depots, praeparate, …). |
| `backend/routers/sync.py` | Hybrid-Sync (web-only). |
| `backend/routers/institutions.py` | Multi-Institution / Onboarding / Map. |
| `backend/routers/desktop_sync_auth.py` | Desktop-Sync-Auth. |
| `security_manager.py` | Passwortpolitik, Account-Sperre. |
| `backend/tools/migrate_sqlite_to_mariadb.py` | Migration SQLite -> MariaDB. |
| `backend/web/*` | Legacy Web-MVP-Frontend (statisch). |

## Engine-Switch

```bash
ND_HUB_DB_ENGINE=sqlite      # lokaler / Test-Modus
ND_HUB_DB_ENGINE=mariadb     # Compose-Default, produktionsnah
ND_HUB_DUAL_WRITE_SQLITE=0   # Mirror-Mode aus (default fuer Go-Live)
```

Details: [Migration & Sync](../migration-and-sync/01-sqlite-vs-mariadb.md).

## Hauptverantwortlichkeiten

- **Validierung** von Eingaben (Datum ISO, Bewegungstypen, Filter, Pagination).
- **Audit-Logging** fuer relevante Mutationen.
- **Idempotenz** fuer Sync-Push (`batch_id`) und Imports (`fingerprint`).
- **Sicherheit** ueber Bearer-Tokens, Permissions und gehaertete Admin-Selbstschutzregeln.

## Schnittstellen-Kategorien

```mermaid
flowchart LR
    auth["Auth & User"] --> svc["Domain Services"]
    svc --> stamm["Stammdaten (Depots/Praeparate/Kontakte)"]
    svc --> bewegungen["Bewegungen + Attachments"]
    svc --> reports["Reports & Exporte"]
    svc --> imports["Imports"]
    svc --> emails["E-Mail Drafts/SMTP"]
    svc --> verfall["Verfall + Notifications"]
    svc --> sync["Sync (status/pull/push/ops)"]
    svc --> admin["Admin (Backup/Restore, Audit)"]
    svc --> institutions["Institutions / Onboarding"]
```

Vollstaendige Endpunkt-Referenz: [API Reference](../api-reference/01-rest-endpoints.md).
OpenAPI zur Laufzeit: `GET /openapi.json`.
