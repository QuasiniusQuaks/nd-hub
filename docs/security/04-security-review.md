# Security Review

ND-Hub fuehrt dedizierte Security-Reviews fuer Desktop und Web durch.
Diese Seite konsolidiert die Review-Bausteine; die ausfuehrlichen
Originalartefakte sind als Archiv unter
[Archiv](../legacy/index.md) verfuegbar.

## Reviewbereiche (gleiche Struktur fuer Desktop und Web)

| Abschnitt | Inhalt |
|---|---|
| Scope & Baseline | Reproduzierbare Umgebung, `pip freeze` / `npm ls`. |
| Supply Chain & SAST | Malware-/Supply-Chain-Pruefung, `bandit`-Auswertung, JS-/Build-Konfiguration. |
| Dependency / CVE Matrix | Mapping bekannter CVEs auf eingesetzte Versionen, Upgradepfade, EOL-Hinweise. |
| Network & Data Disclosure | Datenfluesse, Telemetrie, Logging-Inhalte. |
| AppSec & Code Review | AuthN/AuthZ, Secrets, SQL/Imports, Backend-Konfiguration. |
| Findings & Retest | Priorisierte Befunde (OWASP/CWE), Massnahmen, Retest. |

## Komponenten und Werkzeuge

### Desktop Client

- Toolset:
    - `pip-audit` -> `desktop-client/security-review/pip-audit-report.txt`
    - `bandit` -> `desktop-client/security-review/bandit-report.json`
    - `pip freeze` -> `desktop-client/security-review/baseline-freeze.txt`
- Erneutes Ausfuehren (Auszug):

```bash
cd desktop-client
python3 -m venv .security-review-venv
. .security-review-venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip freeze > security-review/baseline-freeze.txt
pip-audit --desc | tee security-review/pip-audit-report.txt
bandit -r core nd_hub.py db_manager.py security_manager.py user_management.py \
       apple_dashboard.py apple_theme.py icon_manager.py responsive_widgets.py \
       verfall_widget.py verfallmanager.py populate_nd_hub.py run_backend.py \
       run_notfalldepots.py backend/app.py backend/auth.py backend/config.py \
       backend/database.py ui tools \
       -f json -o security-review/bandit-report.json -q
```

### Webanwendung

- Komponenten:
    - Frontend: Vite 5 + React 18 + TypeScript, Leaflet
      (`ndhub-web/frontend-react/`).
    - Backend: FastAPI + uvicorn (`ndhub-web/backend/`).
    - Deployment: Docker Compose + MariaDB.
- Toolset:
    - `npm audit` und `npm ls` (Frontend).
    - `pip-audit` (Backend).
- Erneutes Ausfuehren (Auszug):

```bash
cd ndhub-web/frontend-react
npm install
npm audit --json > ../security-review/npm-audit-full.json
npm ls --depth=0 > ../security-review/baseline-npm-ls.txt
```

```bash
cd ndhub-web
python3 -m venv .audit-venv
. .audit-venv/bin/activate
pip install -U pip pip-audit
pip install -r requirements.txt
pip-audit --desc | tee security-review/pip-audit-backend.txt
pip freeze > security-review/baseline-backend-freeze.txt
```

## Konsolidierte Sicht: Wesentliche Schutzmechanismen

| Bereich | Massnahme |
|---|---|
| Authentifizierung | bcrypt, Account-Sperre, Force-Sync nur kontrolliert. |
| Autorisierung | Rollen + Depot-Scoping + Selbstschutzregeln. |
| Audit | persistenter Audit-Trail mit Filterzugriff. |
| Datei-Uploads | nur PDFs, max. 10 MB, Format-/Groessenpruefung. |
| Backup | Format-/Groessenpruefung, Pre-Restore-Snapshot. |
| Imports | Idempotenz, Dry-Run, Fehlerklassifizierung. |
| Sync | Idempotenz ueber `batch_id`, tokengesichert, auditiert. |
| DB-Engine-Wechsel | dokumentierter Cutover/Rollback, Smoke-Checklist. |

## Offene Themen / Bewusste Grenzen

- In-memory Token-Store: bei horizontaler Skalierung extern zu loesen.
- Sync v1: keine binaere Attachment-Synchronisation.
- SMTP-Liveversand: optional, projektabhaengig konfigurierbar.

## Verweise

- Originalartefakte (zur historischen Referenz):
    - `desktop-client/security-review/`
    - `ndhub-web/security-review/`
- Konsolidierte AuthN/AuthZ-Sicht: [AuthN & AuthZ](01-authn-authz.md).
- Datenschutz-Empfehlungen: [Datenschutz](02-data-protection.md).
