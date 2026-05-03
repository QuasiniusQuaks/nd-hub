# Session Strategy (Sprint 2 Decision)

Dieses Dokument fixiert das Session-Verhalten fuer den Containerbetrieb.

## Aktueller Stand

- Sessions werden ueber `TokenStore` im Prozessspeicher gehalten.
- Ein Backend-Neustart invalidiert bestehende Tokens.

## Entscheidung fuer Sprint 2

- Kurzfristig bleibt der in-memory TokenStore aktiv.
- Das Verhalten bei Neustart wird als bewusstes MVP-Verhalten dokumentiert.
- Frontend/Desktop muessen bei `401` automatisch auf Login zurueckfuehren.

## Akzeptanzkriterium Sprint 2

- Neustartfall ist reproduzierbar:
  - laufende Sessions werden ungueltig
  - Re-Login funktioniert ohne Datenverlust
  - API-Fehlerbild ist konsistent (`401`)

## Upgrade-Pfad (Sprint 5+)

- Option A: persistenter Token-Store in DB (Revocation-freundlich).
- Option B: signierte JWTs mit serverseitiger Revocation-Liste.
- Option C: Redis-basierter Session-Store fuer Multi-Instanz-Betrieb.

Empfehlung fuer Produktionsbetrieb mit mehreren Instanzen: Option C oder
Option B+C (JWT + Revocation Cache).
