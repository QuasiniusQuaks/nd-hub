# Fehlerbehandlung

ND-Hub liefert HTTP-Antworten gemaess REST-Konventionen. Diese Seite
beschreibt die wichtigsten Fehlerbilder und gibt Hinweise zur
Behandlung im Client.

## HTTP-Statuscodes (Auswahl)

| Code | Bedeutung | Typische Ursache |
|---|---|---|
| `200` | OK | Erfolgreiche Anfrage. |
| `201` | Created | Ressource angelegt. |
| `204` | No Content | Erfolgreich, ohne Body. |
| `400` | Bad Request | Validierungsfehler (z. B. Datum nicht ISO). |
| `401` | Unauthorized | Token fehlt oder ungueltig. |
| `403` | Forbidden | Berechtigung fehlt (Rolle/Permission/Depot-Scope). |
| `404` | Not Found | Ressource existiert nicht. |
| `409` | Conflict | Sync-Konflikt oder Konsistenzproblem. |
| `413` | Payload Too Large | z. B. Restore-Upload zu gross (`ND_HUB_MAX_BACKUP_RESTORE_MB`). |
| `415` | Unsupported Media Type | falsches Format (z. B. nicht-PDF Anhang). |
| `422` | Unprocessable Entity | semantische Validierung (z. B. `start_date > end_date`). |
| `429` | Too Many Requests | Rate-Limit (sofern aktiviert). |
| `500` | Internal Server Error | unerwartete Stoerung. |
| `503` | Service Unavailable | DB nicht erreichbar (z. B. waehrend Cutover). |

## Fehlerstruktur

FastAPI liefert standardmaessig ein Schema wie:

```json
{
  "detail": "<Beschreibung oder Validierungsdetails>"
}
```

Bei Validierungsfehlern (`422`) ist `detail` typischerweise eine
Liste mit `loc`, `msg`, `type`-Eintraegen pro Feld.

## Spezielle Fehler

### Import-Vorschau

`POST /imports/bewegungen/preview` liefert eine `error_summary` mit
einem Mapping `by_code`, das Fehlerklassen schnell zaehlbar macht.
Beispiel:

```json
{
  "error_summary": {
    "total": 3,
    "by_code": {
      "INVALID_DATE": 2,
      "MISSING_REQUIRED_FIELD": 1
    }
  }
}
```

### Import-Idempotenz

`POST /imports/bewegungen/execute` reagiert auf einen wiederholten
`import_fingerprint` mit:

```json
{
  "deduplicated": true,
  "fingerprint": "..."
}
```

### Sync-Push

`POST /sync/push` kann pro Change in der Antwort liefern:

```json
{
  "accepted": [...],
  "rejected": [...],
  "conflicts": [...],
  "server_cursor": "..."
}
```

Konflikte enthalten Hinweise gemaess
[Hybrid-Sync](../migration-and-sync/03-hybrid-sync.md).

### Backup-Restore

- `400` / `415`: ungueltiges Format.
- `413`: Datei zu gross.
- `409`: Engine-Fehler (z. B. SQLite-Backup im MariaDB-Modus oder
  umgekehrt).

## Empfehlungen fuer Clients

- 401 -> Login-Flow neu starten.
- 403 -> Berechtigungs-Hinweis fuer den Anwender.
- 4xx allgemein -> Validierung im UI verbessern, ggf. Detail an
  Anwender ausgeben.
- 5xx -> Retry mit exponentiellem Backoff (insb. Sync-Endpunkte).
- Idempotenz-Schluessel (`batch_id`, `import_fingerprint`) konsequent
  verwenden, um Doppelschreiben bei Retry zu vermeiden.
