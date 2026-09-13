# AuthN & AuthZ

ND-Hub nutzt eine durchgehende Auth-Architektur ueber Desktop und Web.

## Authentifizierung

### Login

- Endpunkt: `POST /auth/login` (Web) bzw. lokaler Login im Desktop.
- Methode: Username + Passwort gegen bcrypt-Hashes.
- Resultat: Bearer-Token, Profilinformationen.
- Folgeaufrufe an alle anderen Endpunkte (ausser `/health` und
  `/auth/login`) erfordern den Bearer-Token.

### Token-Store

- Aktuell: in-memory `TokenStore` (siehe
  [Web/Backend / Ueberblick](../web-application/01-overview.md)).
- Konsequenz: Prozessneustart invalidiert aktive Tokens. Fuer
  HA/horizontale Skalierung ist eine externe Session-Strategie
  vorzusehen.

### Passwortpolitik

- bcrypt-Hashes mit angemessenem Cost-Faktor.
- Erzwungener Passwortwechsel bei Erstanmeldung.
- Account-Sperre nach mehrfach fehlgeschlagenen Logins; Freigabe durch
  Admin.
- Passwort-Reset durch Admin moeglich.

### Sonderfall: Admin-Sync

- `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC=1` setzt das Admin-Passwort beim
  Start auf `ND_HUB_INITIAL_ADMIN_PASSWORD` zurueck.
- Beim allerersten Start (kein `admin` in der DB) ist
  `ND_HUB_INITIAL_ADMIN_PASSWORD` Pflicht. Es wird kein Passwort
  generiert und nicht ins Log geschrieben (`__CHANGE_ME__` gilt nicht).
- Nur fuer Notfallzugriff verwenden, anschliessend wieder auf `0`
  zuruecksetzen.

## Autorisierung

### Rollen

| Rolle | Beschreibung |
|---|---|
| Admin | Vollzugriff auf alle administrativen Funktionen. |
| User | Fachanwender. Standardberechtigungen je nach Permissions. |

### Permission-Katalog (Auswahl)

- `depots.write`, `praeparate.write`, `kontakte.write`
- `users.manage`
- `audit.view`
- `backup.manage`

Detaillierte Permissions je Endpunkt sind im Backend-Code definiert
(`ndhub-web/backend/auth.py`).

### Depot-Scoping

- `user_depot_permissions` definiert pro Benutzer und Depot
  `can_read`/`can_write`.
- Endpunkte und UI respektieren diese Scopes
  (`/depots/{id}/*`-Routen, Bewegungen).

### Selbstschutzregeln

- Letzter aktiver Admin kann **nicht** herabgestuft oder deaktiviert
  werden.
- Benutzer koennen sich **nicht selbst** deaktivieren oder die eigene
  Rolle wechseln.

## Sync-Sicherheit

- Sync-Endpunkte sind tokengeschuetzt wie regulaere API-Endpunkte.
- Aenderungen ueber Sync werden auditiert (Akteur, Aktion, Zeit).
- Idempotenz ueber `batch_id` und `cursor` schuetzt vor Doppelschreiben.

## Empfehlungen

- TLS-Terminierung vor `ndhub-web` (Reverse Proxy).
- Starke Passwoerter und regelmaessige Rotation administrativer
  Zugangsdaten.
- Klare Rollenstrategie: nur so viele Admins wie noetig.
- Audit-Logs regelmaessig sichten (siehe [Audit-Logs](03-audit-logs.md)).
