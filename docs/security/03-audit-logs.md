# Audit-Logs

ND-Hub schreibt fachliche Aktionen in einen Audit-Trail, der ueber API
und UI ausgewertet werden kann.

## Was wird auditiert?

- Authentifizierungsereignisse (Login, Logout, Reset, Unlock).
- CRUD-Aktionen auf Stammdaten (`depots`, `praeparate`, `kontakte`,
  Zuordnungen).
- Bewegungen (Anlage, Loeschung, Anhang-Aktionen).
- Importe und E-Mail-Drafts/Versand.
- Backup- und Restore-Aktionen.
- Sync-Aktionen ueber `/sync/*`.

## Speicherort

- Tabelle `api_audit_log` (sowohl in SQLite als auch in MariaDB).
- Felder typischerweise: `timestamp`, `actor`, `action`,
  `resource_type`, `resource_id`, ggf. `payload`-Auszug.

## Zugriff ueber API

- Endpunkt: `GET /audit-logs` (admin-only).
- Filterparameter:
    - `q=<text>`: Volltextsuche.
    - `action=<create|update|delete>`.
    - `resource_type=<type>`.
    - `limit=<n>`, `offset=<n>` (Pagination).
- Rueckgabe enthaelt Eintraege in zeitlicher Reihenfolge mit
  Metadaten.

## Zugriff in der UI

- Web: Admin > Audit (Filter, Pagination, Detailansicht).
- Desktop: Tab "Audit-Logs" unter Grundeinstellungen.

## Sync-Audit-Operations

- `GET /sync/ops/stats` liefert Kennzahlen zu Sync-Batches
  (Permission `audit_view`).
- Nuetzlich fuer Beobachtung der Hybrid-Sync-Stabilitaet.

## Empfehlungen

- Audit-Logs regelmaessig sichten und archivieren.
- Bei sicherheitsrelevanten Vorfaellen Zeitfenster nach Login-/Reset-
  Aktionen untersuchen.
- Audit-Logs als Unterstuetzung fuer Pruefungen exportieren (Endpunkt-
  Daten in CSV/JSON wandeln, sofern organisatorisch erforderlich).
