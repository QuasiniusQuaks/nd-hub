# Phase 4: Anwendungs-Security und Betrieb

## Authentifizierung / Autorisierung (Web-Stack)

- Die SPA delegiert an das **FastAPI-Backend** (gleiches Muster wie Desktop-Client-Backend): Login, Bearer-Token, rollen-/rechtebasierte Endpunkte.
- **Serverseitige** Enforcement bleibt maßgeblich; das Frontend blendet Admin-UI nur über Permissions ein – Backend muss jede Mutation absichern (analog zum Review unter `desktop-client/security-review/04-APPSEC-CODE-REVIEW.md`).

## Secrets und Konfiguration

| Thema | Befund |
|--------|--------|
| **`.env`** | Enthält typischerweise Passwörter/Secrets. Im Repo-Root lag eine `.env`-Datei (Review-Umgebung) – **nicht** in Versionskontrolle committen. Neu: [`.gitignore`](../.gitignore) ignoriert `.env`; bestehend getrackte Dateien ggf. mit `git rm --cached .env` entfernen. |
| **Docker Compose** | Standard-Platzhalter-Passwörter (`ChangeMe`, `ChangeMeToAStrongPassword_123!`) – in **Produktion** überschreiben; keine Defaults auf öffentlich erreichbaren Hosts. |
| **SMTP** | Über Umgebungsvariablen wie im [Backend-README](../backend/README.md); gleiche Klartext-Risiken wie Desktop. |

## Docker / Netzwerk-Exposition

Aus [`docker-compose.yml`](../docker-compose.yml):

| Service | Port-Mapping | Risiko |
|---------|--------------|--------|
| `ndhub-web` | `8000:8000` | HTTP-API weltweit erreichbar, wenn Host öffentlich – **TLS-Terminierung** (Reverse-Proxy) und **Authentifizierung** erzwingen. |
| `mariadb` | `3306:3306` | **Hoch:** Datenbank direkt auf Host-Interface gebunden. Für die meisten Deployments **kein** Host-Port nötig (nur internes Docker-Netz). Empfehlung: `ports`-Sektion für MariaDB entfernen oder auf `127.0.0.1:3306:3306` beschränken. |

`ND_HUB_BACKEND_HOST: 0.0.0.0` im Container ist für internes Listening üblich; Schutz durch Firewall/Proxy.

## Dateien / Uploads

- SPA nutzt `fetch` für Anhänge und Backup-Restore – Größenlimits und Berechtigungen werden **serverseitig** durchgesetzt (`ND_HUB_MAX_BACKUP_RESTORE_MB` etc.); Backend-Code bei Änderungen erneut prüfen.

## Content Security Policy (empfohlen)

- Für ausgeliefertes `index.html` / statische Assets: CSP-Header setzen (`default-src 'self'`, Karten: `img-src` für `*.tile.openstreetmap.org`, ggf. `connect-src`), um XSS-Folgen zu begrenzen.
