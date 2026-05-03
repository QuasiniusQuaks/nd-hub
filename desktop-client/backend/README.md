# ND-Hub Backend (MVP)

Minimal FastAPI backend for the solo migration path.

## Start

```bash
python run_backend.py
```

Optional env vars:

- `ND_HUB_DB_PATH`: override SQLite database file path
- `ND_HUB_BACKEND_HOST`: default `127.0.0.1`
- `ND_HUB_BACKEND_PORT`: default `8000`

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

List endpoints support basic filtering/pagination:

- `GET /depots?q=<text>&limit=<n>&offset=<n>`
- `GET /praeparate?q=<text>&limit=<n>&offset=<n>`
- `GET /depots/<id>/zuordnungen` returns all preparations with `assigned` and `sollbestand`
- `GET /bewegungen?q=<text>&typ=<Typ>&limit=<n>&offset=<n>`
- `GET /audit-logs?q=<text>&action=<create|update|delete>&resource_type=<type>&limit=<n>&offset=<n>`

Import:

- Akzeptiert `*.csv`, `*.xlsx`, `*.xls`
- Pflichtspalten: `Depot`, `Praeparat`, `Typ`, `Charge`, `Verfall`, `Datum`, `Anzahl`
- Optional: `Empfaenger`

PDF-Anhaenge:

- Nur `*.pdf` und max. 10 MB
- Metadaten (`datei_name`, `datei_groesse`, `datei_hochgeladen_am`, `has_attachment`) sind in `GET /bewegungen` enthalten

