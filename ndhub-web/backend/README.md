# ND-Hub Backend (MVP / Doku v0.5, Web-Release 0.1.1)

FastAPI backend fuer ND-Hub Web mit SQLite- und MariaDB-Betriebsmodus.

## Start

```bash
python run_backend.py
```

Optional env vars:

- `ND_HUB_DB_PATH`: override SQLite database file path
- `ND_HUB_ATTACHMENTS_DIR`: override attachment base directory
- `ND_HUB_BACKUPS_DIR`: override backups directory
- `ND_HUB_BACKEND_HOST`: default `127.0.0.1`
- `ND_HUB_BACKEND_PORT`: default `8000`
- `ND_HUB_INITIAL_ADMIN_PASSWORD`: initial admin password seed
- `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC`: force one-time admin password sync on startup (`0`/`1`)
- `ND_HUB_AUTO_BACKUP_HOURS`: auto backup interval in hours
- `ND_HUB_MAX_BACKUP_RESTORE_MB`: max. Upload-Groesse fuer Restore-Dateien
- `ND_HUB_CORS_ORIGINS`: Komma-getrennte CORS-Allowlist (z.B. `https://app.example.com,https://admin.example.com`). Default: leer = Cross-Origin-Requests blockiert. Same-Origin-Traffic funktioniert immer.
- `ND_HUB_ALLOWED_HOSTS`: Komma-getrennte Liste erlaubter `Host`-Header (z.B. `api.example.com,admin.example.com`). Default: `*` = alle Hosts. Produktiv bitte explizit setzen.
- `ND_HUB_EMAIL_DELIVERY_MODE`: `draft` (default) or `smtp`
- `ND_HUB_SMTP_HOST`, `ND_HUB_SMTP_PORT`
- `ND_HUB_SMTP_USERNAME`, `ND_HUB_SMTP_PASSWORD`
- `ND_HUB_SMTP_USE_TLS`, `ND_HUB_SMTP_USE_SSL`
- `ND_HUB_SMTP_FROM_ADDRESS`, `ND_HUB_SMTP_FROM_NAME`
- `ND_HUB_SMTP_TIMEOUT_SECONDS`

MariaDB-/Engine-Optionen:

- `ND_HUB_DB_ENGINE` (`sqlite` or `mariadb`)
- `ND_HUB_MARIADB_HOST`
- `ND_HUB_MARIADB_PORT`
- `ND_HUB_MARIADB_DATABASE`
- `ND_HUB_MARIADB_USER`
- `ND_HUB_MARIADB_PASSWORD`
- `ND_HUB_DUAL_WRITE_SQLITE` (`1` mirrors writes to SQLite fallback, `0` disables mirror; Go-Live default: `0`)

## Docker Compose

Default-Stack (MariaDB **ohne** Compose-Profile — Service ist immer definiert):

```bash
# Secrets in .env setzen (Pflicht: ND_HUB_MARIADB_PASSWORD, ND_HUB_MARIADB_ROOT_PASSWORD).
# Leere Werte: Compose bricht ab. Kein Default-Passwort.
docker compose up -d --build
```

Engine-Umschaltung:

```bash
# Compose-Default
ND_HUB_DB_ENGINE=mariadb

# Lokaler/Dev-SQLite-Modus (MariaDB-Service kann ungenutzt bleiben)
ND_HUB_DB_ENGINE=sqlite
```

Hinweis: Aeltere Docs erwaehnten `docker compose --profile mariadb` — das trifft
auf den aktuellen `docker-compose.yml` **nicht** zu (kein `profiles:` am MariaDB-Service).
Root-README und Deployment-Doku sind Source of Truth.

Fuer Umstieg/Betrieb gelten Runbook und Smoke-Checklist.

## Aktueller Cutover-Stand (inkrementell)

- Bei `ND_HUB_DB_ENGINE=mariadb` nutzt das Backend einen MariaDB-Repository-Pfad
  fuer Kern-CRUD-Flows (Depots, Praeparate, Kontakte, Bewegungen, E-Mail-Verlauf, Audit).
- Noch nicht portierte, komplexe Auswertungslogik wird temporaer ueber SQLite-Fallback
  bedient, um Funktionsparitaet waehrend der Migration zu halten.
- Schreibvorgaenge in den portierten Kernfluesse werden dual in MariaDB und SQLite
  gespiegelt (Uebergangsmodus).
- Das Spiegeln laesst sich ueber `ND_HUB_DUAL_WRITE_SQLITE` kontrollieren.
- Nach erfolgreichem Cutover und verifizierten Smoke-Checks sollte
  `ND_HUB_DUAL_WRITE_SQLITE=0` gesetzt bleiben.

## Migration SQLite -> MariaDB (Sprint 3)

Migrationsskript:

```bash
python -m backend.tools.migrate_sqlite_to_mariadb --sqlite /data/nd_hub_backend.db
```

Quellanalyse ohne MariaDB-Verbindung (Dry-run):

```bash
python -m backend.tools.migrate_sqlite_to_mariadb --sqlite /data/nd_hub_backend.db --dry-run
```

Cutover-Ablauf:

- Konsolidierter Pfad: [Migration & Sync / MariaDB-Cutover](../../docs/migration-and-sync/02-mariadb-cutover.md).
- Originaldokumente sind unter [`docs/legacy/ndhub-web/`](../../docs/legacy/index.md) archiviert.

Backup/Restore im MariaDB-Mode:

- `POST /admin/backup/create` erstellt logische Backups als `*.mariadb.json`
- `POST /admin/backup/restore` erwartet `*.mariadb.json` oder `*.json`
- Restore-Uploads werden groessenbegrenzt geprueft (`ND_HUB_MAX_BACKUP_RESTORE_MB`)

## Endpoints

- `GET /` (Web-MVP client)
- `GET /web/*` (static web assets)
- `GET /health`
- `POST /auth/login`
- `GET /auth/me`
- `GET /dashboard/overview`
- `GET /depots`
- `POST /depots`
- `PUT /depots/{id}`
- `DELETE /depots/{id}`
- `GET /praeparate`
- `POST /praeparate`
- `PUT /praeparate/{id}`
- `DELETE /praeparate/{id}`
- `GET /depots/{id}/zuordnungen`
- `PUT /depots/{id}/zuordnungen` (admin)
- `GET /depots/{id}/kontakte`
- `POST /depots/{id}/kontakte` (admin)
- `PUT /kontakte/{id}` (admin)
- `DELETE /kontakte/{id}` (admin)
- `POST /emails/recipients-preview`
- `GET /emails/delivery/status`
- `POST /emails/drafts`
- `GET /emails/history`
- `GET /emails/history/{id}`
- `GET /reports/bewegungen`
- `GET /reports/bewegungen/export.csv`
- `GET /reports/bewegungen/export.pdf`
- `GET /reports/bewegungen/export.pptx`
- `GET /reports/bestand`
- `GET /reports/bestand/export.csv`
- `GET /reports/bestand/export.pdf`
- `GET /reports/bestand/export.pptx`
- `GET /reports/ranking`
- `GET /reports/ranking/export.csv`
- `GET /reports/ranking/export.pdf`
- `GET /reports/ranking/export.pptx`
- `GET /reports/matrix`
- `GET /reports/matrix/export.csv`
- `GET /reports/matrix/export.pdf`
- `GET /reports/matrix/export.pptx`
- `GET /reports/verfall`
- `GET /reports/verfall/export.csv`
- `GET /reports/verfall/export.pdf`
- `GET /reports/verfall/export.pptx`
- `GET /verfall/overview`
- `GET /verfall/overview/export.csv`
- `GET /notifications/verfall`
- `POST /imports/bewegungen/preview` (CSV/Excel-Vorschau)
- `POST /imports/bewegungen/execute` (CSV/Excel-Import)
- `GET /imports/bewegungen/template` (Excel-Vorlage)
- `GET /bewegungen`
- `POST /bewegungen`
- `POST /bewegungen/{id}/attachment` (PDF-Upload)
- `GET /bewegungen/{id}/attachment` (inline anzeigen)
- `GET /bewegungen/{id}/attachment?download=true` (Download)
- `GET /audit-logs` (admin only)

All endpoints except `/health` and `/auth/login` require a bearer token.
Write endpoints for depots/praeparate require admin role.
`POST /bewegungen` validates `datum` and `verfall` as ISO date (`YYYY-MM-DD`).
User-Admin-Hardening: letzter aktiver Admin kann weder herabgestuft/deaktiviert werden,
und ein Benutzer kann sich nicht selbst deaktivieren oder die eigene Rolle wechseln.

List endpoints support basic filtering/pagination:

- `GET /depots?q=<text>&limit=<n>&offset=<n>`
- `GET /praeparate?q=<text>&limit=<n>&offset=<n>`
- `GET /depots/<id>/zuordnungen` returns all preparations with `assigned` and `sollbestand`
- `GET /bewegungen?q=<text>&typ=<Typ>&depot_id=<id>&praeparat_id=<id>&has_attachment=<0|1>&start_date=<YYYY-MM-DD>&end_date=<YYYY-MM-DD>&limit=<n>&offset=<n>`
- `GET /bewegungen/export.csv?q=<text>&typ=<Typ>&depot_id=<id>&praeparat_id=<id>&has_attachment=<0|1>&start_date=<YYYY-MM-DD>&end_date=<YYYY-MM-DD>`
- `GET /audit-logs?q=<text>&action=<create|update|delete>&resource_type=<type>&limit=<n>&offset=<n>`
- `GET /sync/ops/stats` (Audit/Ops Kennzahlen fuer Sync-Batches; Permission `audit_view`)
- Report-Endpunkte mit Datum (`start_date`, `end_date`) validieren ISO-Format und Reihenfolge (`start_date <= end_date`)
- Report-Exporte liefern kontextreiche Dateinamen (Typ/Perspektive/Zeitraum)

Import:

- Akzeptiert `*.csv`, `*.xlsx`, `*.xls`
- Pflichtspalten: `Depot`, `Praeparat`, `Typ`, `Charge`, `Verfall`, `Datum`, `Anzahl`
- Optional: `Empfaenger`
- `POST /imports/bewegungen/preview` liefert `error_summary.by_code` fuer schnellere Fehlerklassifizierung.
- `POST /imports/bewegungen/execute` ist idempotent pro Importinhalt (`import_fingerprint`) und gibt bei Wiederholung `deduplicated=true` zurueck.
- `POST /imports/bewegungen/execute` unterstuetzt `dry_run=true` (validiert und simuliert, ohne DB-Schreibvorgaenge).

E-Mail:

- `POST /emails/drafts` erstellt immer einen Verlaufseintrag (Draft als Fallback).
- Optional kann `send_now=true` gesetzt werden.
- Bei `ND_HUB_EMAIL_DELIVERY_MODE=smtp` wird ein Live-Versand versucht.
- Versandstatus (`versand_status`, `versand_kanal`, `versand_fehler`) ist im E-Mail-Verlauf enthalten.

PDF-Anhaenge:

- Nur `*.pdf` und max. 10 MB
- Metadaten (`datei_name`, `datei_groesse`, `datei_hochgeladen_am`, `has_attachment`) sind in `GET /bewegungen` enthalten

## Architekturartefakte und Betrieb

Die Detailartefakte wurden in die Enterprise-Dokumentation
ueberfuehrt. Konsolidierte Einstiegspunkte:

- Architektur und Datenmodell: [`docs/architecture/`](../../docs/architecture/index.md)
- Deployment / Docker: [`docs/deployment/01-docker-stack.md`](../../docs/deployment/01-docker-stack.md)
- Migration & Sync: [`docs/migration-and-sync/`](../../docs/migration-and-sync/index.md)
- API-Referenz: [`docs/api-reference/01-rest-endpoints.md`](../../docs/api-reference/01-rest-endpoints.md)
- Release Notes / Acceptance: [`docs/project/03-release-notes.md`](../../docs/project/03-release-notes.md), [`docs/quality/02-acceptance-suite.md`](../../docs/quality/02-acceptance-suite.md)

Originaldokumente (Cutover-Runbook, Smoke-Checklist, Migration-Spec,
Dual-Write Note, Sync-Contract, Session-Strategy, Docker-Target-Profile,
Desktop-Parity-Plan, Release-Notes-Originale) befinden sich archiviert
unter [`docs/legacy/ndhub-web/`](../../docs/legacy/index.md).

## Hybrid-Sync E2E Test

- Der Integrationspfad `offline write -> push -> pull apply` ist als Test vorhanden:
  - `backend/tests/test_sync_hybrid_e2e.py`
- Ausfuehren (vom **Repository-Root**, mit `ndhub-web/` und `desktop-client/` als Geschwister):
  - `PYTHONPATH="ndhub-web:desktop-client" python3 -m pytest "ndhub-web/backend/tests/test_sync_hybrid_e2e.py"`

## Stability/Acceptance Regression

- Kernsuite fuer Session/Security + gehaertete Kernfluesse:
  - `PYTHONPATH="ndhub-web" ./.venv-sync-tests/bin/python -m pytest ndhub-web/backend/tests/test_stability_acceptance.py ndhub-web/backend/tests/test_user_admin_hardening.py ndhub-web/backend/tests/test_report_export_hardening.py ndhub-web/backend/tests/test_backup_restore_hardening.py ndhub-web/backend/tests/test_import_idempotency.py ndhub-web/backend/tests/test_email_delivery.py ndhub-web/backend/tests/test_bewegungen_filters.py ndhub-web/backend/tests/test_sync_ops_stats.py ndhub-web/backend/tests/test_sync_hybrid_e2e.py`

