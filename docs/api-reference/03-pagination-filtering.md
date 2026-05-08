# Pagination & Filter

ND-Hub-Listenendpunkte folgen einem einheitlichen Muster fuer
Pagination und Filterung.

## Pagination

| Parameter | Beschreibung |
|---|---|
| `limit` | maximale Anzahl Datensaetze pro Seite (Default je Endpunkt). |
| `offset` | Versatz ab dem Anfang der Ergebnismenge. |

Beispiel:

```
GET /depots?q=apo&limit=50&offset=100
```

Antwort enthaelt eine Liste; die Gesamtmenge wird in vielen Endpunkten
ueber Metadatenfelder oder ueber den HTTP-Header zurueckgegeben (siehe
einzelne Endpunkte).

## Volltextsuche (`q`)

- Verfuegbar auf `/depots`, `/praeparate`, `/bewegungen`, `/audit-logs`.
- Sucht in fachlich sinnvollen Feldern (Name, Beschreibung, Charge,
  Empfaenger ...).
- Klein-/Grossschreibung wird in der Regel ignoriert.

## Bewegungen-Filter

Filterbare Felder fuer `GET /bewegungen` und
`GET /bewegungen/export.csv`:

- `q=<text>`
- `typ=<Zugang|Abgang|Vernichtung>`
- `depot_id=<id>`, `praeparat_id=<id>`
- `has_attachment=<0|1>`
- `start_date=<YYYY-MM-DD>`, `end_date=<YYYY-MM-DD>`
- `limit`, `offset`

Datumsvalidierung:

- ISO-Format `YYYY-MM-DD`.
- `start_date <= end_date` zwingend.

## Reports

Reportendpunkte (`/reports/*`) akzeptieren in der Regel die gleichen
Datumsfilter (`start_date`, `end_date`) und liefern bei den
Export-Routen kontextreiche Dateinamen.

## Audit-Logs

`GET /audit-logs` Filter:

- `q=<text>`
- `action=<create|update|delete>`
- `resource_type=<type>`
- `limit`, `offset`

## Idempotenz und Sync

- `POST /sync/push` benoetigt `batch_id` (UUID) zur Wiederholungssicherheit.
- `POST /imports/bewegungen/execute` nutzt `import_fingerprint` aus dem
  Importinhalt.
- Wiederholungen mit identischem Schluessel liefern strukturierte
  Hinweise (z. B. `deduplicated=true`).

## Designhinweis fuer eigene Integrationen

Wenn eigene Tools die API nutzen:

1. Filter und Pagination kombinieren statt grosse Mengen ohne `limit`
   abzuholen.
2. Fehlerbehandlung gemaess
   [Fehlerbehandlung](02-error-model.md) implementieren.
3. Bei Massenoperationen Idempotenzschluessel verwenden.
