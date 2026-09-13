# Runbooks

Diese Seite buendelt operative Standardablaeufe.

## Stack starten / stoppen

Ohne gesetztes `ND_HUB_MARIADB_PASSWORD` und `ND_HUB_MARIADB_ROOT_PASSWORD`
startet Compose nicht (fail-closed, Issue #104). Es gibt kein Default-Passwort —
auch nicht `changeme`. Platzhalter aus `.env.example` ersetzen, dann starten.

```bash
cd ndhub-web
cp .env.example .env   # Passwoerter setzen, nichts leer lassen
docker compose up -d --build
docker compose down                    # ohne Volume-Loeschung
docker compose down -v                 # mit Volumes (DESTRUCTIVE)
```

## Logs einsehen

```bash
docker compose logs -f ndhub-web
docker compose logs -f mariadb
```

## Healthcheck pruefen

`ndhub-web` published `8000` nur auf `127.0.0.1` (Issue #108). NPM/Pangolin
auf dem NAS-Host verbinden lokal; LAN umgeht die Proxy-Kette nicht.
Ausnahme: `ND_HUB_WEB_BIND=0.0.0.0` in `.env`, wenn Pangolin den App-Port
direkt auf der NAS ansteuert.

```bash
curl http://localhost:8000/health
```

## Adminkonto entsperren

1. `.env` anpassen:
   - `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC=1`
   - `ND_HUB_INITIAL_ADMIN_PASSWORD=<neues sicheres Passwort>`
2. Stack neu starten: `docker compose up -d --build`.
3. Mit dem neuen Passwort einloggen.
4. `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC=0` zuruecksetzen und neu starten.

## Manuelles Backup ausloesen

- UI: Admin > Backup > "Backup erstellen".
- API: `POST /admin/backup/create` (admin-only).

Backup-Dateien liegen im Volume `ndhub_backups` (`/data/backups` im
Container).

## Restore eines Backups

- UI: Admin > Backup > Datei auswaehlen > Restore bestaetigen.
- API: `POST /admin/backup/restore` (admin-only) mit Multipart-Upload.
- Das System erzeugt vorab einen Pre-Restore-Snapshot.
- Format und Groesse werden geprueft (`ND_HUB_MAX_BACKUP_RESTORE_MB`).

Anschliessend Smoke-Test:

- Login pruefen.
- Bewegungs-Liste laden.
- Reports anstossen.

## SMTP-Versand aktivieren

1. SMTP-Variablen in `.env` setzen
   (`ND_HUB_SMTP_HOST`, `ND_HUB_SMTP_PORT`, `ND_HUB_SMTP_USERNAME`,
   `ND_HUB_SMTP_PASSWORD`, `ND_HUB_SMTP_FROM_*`,
   `ND_HUB_SMTP_USE_TLS=1`).
2. `ND_HUB_EMAIL_DELIVERY_MODE=smtp` setzen.
3. Stack neu starten.
4. Test-Mail aus der Anwendung versenden (`send_now=true`).
5. Versandstatus im E-Mail-Verlauf pruefen
   (`versand_status`, `versand_kanal`, `versand_fehler`).

## Auto-Backup-Intervall aendern

- `ND_HUB_AUTO_BACKUP_HOURS=12` in `.env` setzen.
- Stack neu starten.

## Datenbank-Engine wechseln

- Vor jedem Wechsel: aktuelles Backup erstellen.
- Wechsel SQLite -> MariaDB: siehe
  [Migration & Sync / MariaDB-Cutover](../migration-and-sync/02-mariadb-cutover.md).
- Wechsel MariaDB -> SQLite (Rollback): `ND_HUB_DB_ENGINE=sqlite`,
  Service neu starten, ggf. SQLite aus Backup wiederherstellen.

## Container-Neustart erzwingen

```bash
cd ndhub-web
docker compose restart ndhub-web
```

## Volumes inspizieren

```bash
docker volume ls | grep ndhub
docker volume inspect ndhub-web_ndhub_mariadb_data
```

## Emergency-Read-only-Modus

Falls fachliche Schreibzugriffe pausiert werden sollen (z. B. Cutover,
Wartung):

- Reverse Proxy auf Wartungsseite umschalten oder
- Schreibrechte ueber Rollen/Permissions vorruebergehend entziehen.

ND-Hub kennt keinen globalen Read-only-Schalter; die Massnahme erfolgt
betrieblich.
