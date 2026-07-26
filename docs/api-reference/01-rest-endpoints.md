# REST-Endpunkte

Diese Seite enthaelt eine konsolidierte Uebersicht aller wichtigen
Endpunkte. **Quellen (v0.5 / ndhub-web 0.1.1):**

- Factory: `ndhub-web/backend/app_factory.py` (+ duenner Shim `backend/app.py`)
- Domain-Router: `shared/routers/*`
- Web-only: `ndhub-web/backend/routers/sync.py`, `institutions.py`, `desktop_sync_auth.py`
- Kurzuebersicht: `ndhub-web/backend/README.md`
- **Source of Truth zur Laufzeit:** `GET /openapi.json`

Alle Endpunkte ausser `GET /health` und
`POST /auth/login` erfordern einen Bearer-Token.

## System

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/` | Web-MVP Startseite. |
| `GET` | `/web/*` | Statische Web-Assets. |
| `GET` | `/health` | Healthcheck (HTTP 200 erwartet). |

## Authentifizierung & Benutzer

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/auth/login` | Login (Username + Passwort). |
| `GET` | `/auth/me` | Profil des angemeldeten Benutzers. |
| `POST` | `/auth/change-password` | Passwortwechsel. |
| `POST` | `/auth/avatar` | Avatar-Upload. |
| `GET`/`POST`/... | `/users*` | Benutzerverwaltung (admin-only). |
| `POST` | `/auth/desktop-sync-token` | Erzeugen eines Desktop-Sync-Tokens (admin-only). |
| `GET`/`DELETE` | `/auth/desktop-sync-token*` | Verwaltung von Sync-Tokens. |

## Dashboard

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/dashboard/overview` | KPIs und Aktivitaetsdaten fuer das Dashboard. |

## Stammdaten

### Depots

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/depots` | Liste mit `q`, `limit`, `offset`. |
| `POST` | `/depots` | Anlage (admin-only). |
| `PUT` | `/depots/{id}` | Update (admin-only). |
| `DELETE` | `/depots/{id}` | Loeschen (admin-only). |
| `GET` | `/depots/{id}/zuordnungen` | Praeparate-Zuordnungen mit Sollbestand. |
| `PUT` | `/depots/{id}/zuordnungen` | Zuordnungen aendern (admin). |
| `GET` | `/depots/{id}/kontakte` | Kontakte je Depot. |
| `POST` | `/depots/{id}/kontakte` | Kontakt anlegen (admin). |

### Praeparate

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/praeparate` | Liste mit `q`, `limit`, `offset`. |
| `POST` | `/praeparate` | Anlage (admin-only). |
| `PUT` | `/praeparate/{id}` | Update (admin-only). |
| `DELETE` | `/praeparate/{id}` | Loeschen (admin-only). |

### Kontakte

| Methode | Pfad | Beschreibung |
|---|---|---|
| `PUT` | `/kontakte/{id}` | Update (admin). |
| `DELETE` | `/kontakte/{id}` | Loeschen (admin). |

## Bewegungen

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/bewegungen` | Liste mit Filtern und Pagination. |
| `POST` | `/bewegungen` | Bewegung anlegen (Datumsvalidierung). |
| `POST` | `/bewegungen/{id}/attachment` | PDF-Anhang hochladen (max. 10 MB). |
| `GET` | `/bewegungen/{id}/attachment` | Anhang inline anzeigen. |
| `GET` | `/bewegungen/{id}/attachment?download=true` | Anhang herunterladen. |
| `GET` | `/bewegungen/export.csv` | CSV-Export der gefilterten Liste. |

Filter-Parameter (Auswahl):

- `q=<text>`
- `typ=<Zugang|Abgang|Vernichtung>`
- `depot_id=<id>`, `praeparat_id=<id>`
- `has_attachment=<0|1>`
- `start_date`, `end_date` (ISO `YYYY-MM-DD`)
- `limit`, `offset`

## Verfall

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/verfall/overview` | Uebersicht inkl. Kategorien. |
| `GET` | `/verfall/overview/export.csv` | CSV-Export. |
| `GET` | `/notifications/verfall` | Polling-Notifications. |

## Reports und Exporte

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/reports/bewegungen` | Auswertung Bewegungen. |
| `GET` | `/reports/bewegungen/export.{csv\|pdf\|pptx}` | Exporte. |
| `GET` | `/reports/bestand` | Auswertung Bestand. |
| `GET` | `/reports/bestand/export.{csv\|pdf\|pptx}` | Exporte. |
| `GET` | `/reports/ranking` | Auswertung Ranking. |
| `GET` | `/reports/ranking/export.{csv\|pdf\|pptx}` | Exporte. |
| `GET` | `/reports/matrix` | Auswertung Matrix. |
| `GET` | `/reports/matrix/export.{csv\|pdf\|pptx}` | Exporte. |
| `GET` | `/reports/verfall` | Auswertung Verfall. |
| `GET` | `/reports/verfall/export.{csv\|pdf\|pptx}` | Exporte. |

Validierung: `start_date` und `end_date` werden gegen ISO-Format und
Reihenfolge geprueft. Exporte verwenden kontextreiche Dateinamen.

## Imports

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/imports/bewegungen/preview` | Vorschau, Validierung, `error_summary.by_code`. |
| `POST` | `/imports/bewegungen/execute` | Idempotenter Import; `dry_run=true` moeglich. |
| `GET` | `/imports/bewegungen/template` | Excel-Vorlage. |

## E-Mail

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/emails/recipients-preview` | Empfaengeraggregation pro Depot. |
| `GET` | `/emails/delivery/status` | Aktueller Versandmodus. |
| `POST` | `/emails/drafts` | Draft-Erstellung; optional `send_now=true`. |
| `GET` | `/emails/history` | Verlauf. |
| `GET` | `/emails/history/{id}` | Einzelner Verlaufseintrag. |

## Sync

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/sync/status` | Server-Zeit, Mindestversionen, Features. |
| `POST` | `/sync/pull` | Inkrementeller Pull mit Cursor. |
| `POST` | `/sync/push` | Idempotenter Push (`batch_id`). |
| `GET` | `/sync/ops/stats` | Sync-/Audit-Kennzahlen (Permission `audit_view`). |

## Onboarding (optional)

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/onboarding/status` | Status der Erstkonfiguration. |
| `POST` | `/onboarding/institution-setup` | Institution initial einrichten. |

## Geo & Map (optional, Feature-Flags)

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/geo/geocode` | Geocoding-Helper. |
| `GET` | `/map/institutions` | Institutionen fuer Kartenansicht. |

## Admin / Backup

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/admin/backup/create` | Manuelles Backup. |
| `GET` | `/admin/backup/list` | Liste der Backups. |
| `GET` | `/admin/backup/download/{name}` | Download. |
| `POST` | `/admin/backup/restore` | Restore (Format-/Groessenpruefung). |

## Audit

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/audit-logs` | Filter (`action`, `resource_type`, `q`), Pagination. |
