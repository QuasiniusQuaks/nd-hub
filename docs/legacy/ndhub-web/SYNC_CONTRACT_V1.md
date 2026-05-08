!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# Desktop-Backend Sync Contract v1 (Sprint 1 Draft)

Dieses Dokument definiert den API-basierten Synchronisationsvertrag zwischen
Desktop-Client und `ndhub-web` Backend.

## Ziele

- Desktop synchronisiert ausschliesslich ueber API, nicht ueber direkten DB-Zugriff.
- Synchronisation bleibt nach SQLite->MariaDB Migration unveraendert nutzbar.
- Idempotenz und Wiederaufnahme nach Netzunterbrechungen sind verpflichtend.
- Desktop bleibt auch ohne Serverinstanz voll lokal arbeitsfaehig (SQLite bleibt Write-Store).

## Client-Betriebsmodi (neu)

- `local_only`:
  - Desktop schreibt und liest ausschliesslich lokal in SQLite.
  - Keine Pflicht zur Backend-Erreichbarkeit.
  - Outbox kann optional lokal befuellt werden, wird aber nicht automatisch gepusht.
- `hybrid_sync`:
  - Desktop ist lokal zuerst (SQLite bleibt source-of-truth waehrend Offline-Phase).
  - Bei erreichbarem Backend werden lokale Outbox-Aenderungen gepusht und Server-Aenderungen gepullt.
  - Bei Netz-/Serverausfall faellt der Client ohne Schreibunterbrechung auf lokal zurueck.
- `remote_only`:
  - Nur fuer Sonderfaelle; bei fehlender Servererreichbarkeit sind Writes gesperrt.
  - Kein Standard fuer Einsatzszenarien mit Offline-Anforderung.

## Translational Layer (Desktop)

- Der Desktop erhaelt einen Data-Access-Router vor dem Sync-Service.
- Aufgaben:
  - Laufzeitentscheidung lokal vs. remote je nach Betriebsmodus und Healthcheck.
  - Lokale Writes in SQLite immer zulassen (`local_only`, `hybrid_sync`).
  - Sync-faehige Aenderungen in lokaler Outbox speichern (dedupefaehig ueber Schluessel).
  - Push/Pull-Batches idempotent gegen Backend-Sync-Endpunkte ausfuehren.
- Wichtig: Das ist eine Client-Schicht und ersetzt nicht den Backend-Dual-Write.

## Domain-Scope fuer v1

- Stammdaten: `depots`, `praeparate`, `depot_praeparate`, `kontakte`
- Bewegungen: `bewegungen` (ohne binaere Attachment-Dateien im ersten Schritt)
- Metadaten: Sync-Cursor, Konfliktinformationen, Server-Timestamps

## Datenmodell-Sicht fuer Sync

- Jede sync-relevante Entitaet hat:
  - `id`
  - `updated_at` (UTC)
  - `deleted_at` (optional fuer soft delete / tombstone)
  - `version` (integer oder monotones Update-Feld)

## Endpunktvorschlag v1

- `POST /sync/pull`
  - Request: `{ cursor, entities, limit }`
  - Response: `{ next_cursor, changes: [{ change_id, entity, operation, payload, changed_at }], has_more }`
- `POST /sync/push`
  - Request: `{ batch_id, changes: [ ... ] }`
  - Response: `{ accepted, rejected, conflicts, server_cursor }`
- `GET /sync/status`
  - Response: `{ server_time, min_supported_client_version, features }`

## Implementierungsstand (aktuell)

- `GET /sync/status` ist implementiert.
- `POST /sync/pull` ist implementiert als inkrementeller Audit-Changefeed mit Cursor.
- `POST /sync/push` ist implementiert mit idempotenter Batch-Deduplizierung (`batch_id`).
- Push-Changeformat:
  - `entity`: `depots|praeparate|kontakte|bewegungen`
  - `operation`: `create|update|delete` (bei `bewegungen` in v1 nur `create`)
  - `payload`: fachliche Felder je Entity
  - optional `client_change_id` fuer Client-Korrelation

## Idempotenz und Reihenfolge

- Jeder Push-Batch enthaelt `batch_id` (UUID).
- Server speichert verarbeitete `batch_id` fuer deduplizierte Wiederholungen.
- Gleicher `batch_id` darf bei Retry kein doppeltes Schreiben ausloesen.

## Konfliktregeln v1

- `update/update`: Last-write-wins mit Konflikthinweis an Client.
- `delete/update`: delete gewinnt, update wird als Konflikt zurueckgegeben.
- `create/create` mit fachgleichem Schluessel: serverseitige Dublettenregel, Konflikt an Client.

## Fehlerverhalten

- Teilweise Batch-Verarbeitung erlaubt, aber Ergebnis muss pro Change eindeutig sein.
- Client speichert `rejected/conflicts` lokal und markiert Datensaetze fuer Nacharbeit.
- 5xx fuehrt zu Retry mit Backoff; 4xx wird als fachlicher Fehler behandelt.

## Security

- Sync-Endpunkte sind token-geschuetzt wie andere Fachendpunkte.
- Jede Aenderung wird auditiert (Akteur, Aktion, Objekt, Zeit).
- Rate-Limits fuer grosse Push-Batches in spaeterer Phase einplanen.

## Nicht-Ziele fuer v1

- Keine bidirektionale Attachment-Dateisynchronisation.
- Kein vollautomatisches Konflikt-UI im ersten Schritt.
- Kein Multi-Master mit gleichzeitiger Vollschreibfaehigkeit mehrerer Offline-Clients.

## Abnahmekriterien v1

- Pull seit `cursor` liefert konsistente Aenderungsmenge ohne Luecken.
- Push ist idempotent unter Retry und Netzunterbrechung.
- Konflikte sind reproduzierbar und maschinenlesbar markiert.
- Migration auf MariaDB aendert den Sync-Vertrag nicht.
- `local_only` funktioniert ohne laufendes Backend, inklusive lokaler Persistenz.
- `hybrid_sync` schreibt bei Offline weiter lokal und synchronisiert nach Wiederverbindung ohne Duplikate.
