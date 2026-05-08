# Webanwendung: Funktionen

Diese Seite beschreibt die fachlichen Funktionen der Webanwendung.
Die Funktionen entsprechen weitgehend dem Desktop Client; serverseitig
wird zusaetzlich eine API fuer Integrationen bereitgestellt.

## Authentifizierung und Benutzer

- Login/Logout, Token-Refresh, Avatar-Upload.
- Passwortregeln, Reset durch Admin, Account-Unlock.
- Selbstschutz: kein Selbstdeaktivieren oder eigene Rolle aendern;
  letzter aktiver Admin geschuetzt.

## Stammdaten

- **Depots**: CRUD, Suche und Pagination
  (`/depots?q=&limit=&offset=`).
- **Praeparate**: CRUD, Suche und Pagination.
- **Zuordnungen**: alle Praeparate je Depot mit `assigned`/`sollbestand`.
- **Kontakte**: CRUD pro Depot.
- **Institutionen** (optional): zentrale Traeger fuer mehrere Depots.

## Bewegungen

- Erfassen ueber `POST /bewegungen` mit Validierung (`datum`/`verfall`
  als ISO).
- Filter ueber `GET /bewegungen?...` (Typ, Depot, Praeparat, Datum,
  Anhang, Volltext, Pagination).
- CSV-Export ueber `/bewegungen/export.csv` mit denselben Filtern.
- PDF-Anhaenge:
  - `POST /bewegungen/{id}/attachment` (max. 10 MB, nur PDF).
  - `GET /bewegungen/{id}/attachment` (inline).
  - `GET /bewegungen/{id}/attachment?download=true` (Download).

## Verfall

- `GET /verfall/overview` mit Kategorisierung.
- CSV-Export `/verfall/overview/export.csv`.
- `GET /notifications/verfall` fuer Polling-Notifications.

## Reports

- Endpunkte: `/reports/bewegungen`, `/reports/bestand`,
  `/reports/ranking`, `/reports/matrix`, `/reports/verfall`.
- Exporte je Report in `CSV`, `PDF`, `PPTX`.
- Strikte Datumsvalidierung (`start_date <= end_date`).
- Kontextreiche Dateinamen.

## Imports

- `POST /imports/bewegungen/preview`: Validierung und
  Fehlerklassifizierung (`error_summary.by_code`).
- `POST /imports/bewegungen/execute`: idempotent ueber
  `import_fingerprint`, optional `dry_run=true`.
- `GET /imports/bewegungen/template`: Excel-Vorlage.

## E-Mail-Workflows

- `POST /emails/recipients-preview`: Empfaengeraggregation pro Depot.
- `POST /emails/drafts`: erstellt immer einen Verlaufseintrag,
  optional `send_now=true` fuer SMTP-Live.
- `GET /emails/history` und `/emails/history/{id}`.
- `GET /emails/delivery/status` fuer den Versandmodus.

## Audit

- `GET /audit-logs` (admin-only) mit Filtern fuer `action`,
  `resource_type`, Volltext und Pagination.

## Backup und Restore (Admin)

- Erstellung: `POST /admin/backup/create`.
- Liste: `GET /admin/backup/list`.
- Restore: `POST /admin/backup/restore` mit Format- und
  Groessenpruefung (`*.mariadb.json` oder `*.json`).
- Auto-Backup-Intervall ueber `ND_HUB_AUTO_BACKUP_HOURS`.

## Sync

- `GET /sync/status` (Server-Zeit, Mindestversionen, Features).
- `POST /sync/pull` mit Cursor.
- `POST /sync/push` mit `batch_id` (idempotent).
- `GET /sync/ops/stats` fuer Ops-Kennzahlen (Permission `audit_view`).

## Karte / Geo (optional)

- `POST /geo/geocode` und `GET /map/institutions` bei aktivem
  Multi-Institution- bzw. Map-Feature
  (`ND_HUB_FEATURE_MULTI_INSTITUTION`,
  `ND_HUB_FEATURE_INSTITUTION_MAP`).

Vollstaendige Endpunkte und Auth-Anforderungen siehe
[API Reference / REST-Endpunkte](../api-reference/01-rest-endpoints.md).
