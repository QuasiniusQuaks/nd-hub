# Docker Target Profile (Sprint 1)

Dieses Dokument definiert das Zielprofil fuer den Docker-Betrieb von `ndhub-web`.
Es ist die Referenz fuer lokale Nutzung, Staging und spaeter Produktion.

## Ziele

- Reproduzierbarer Start ueber `docker compose`.
- Persistente Datenhaltung fuer DB, Uploads und Backups.
- Klarer Health-Status pro Service.
- Trennung von Runtime-Konfiguration und Container-Image.

## Ziel-Topologie

- Service `ndhub-web` (FastAPI + statische WebApp).
- Service `mariadb` (ab Migrationsphase aktiv).
- Optionaler one-shot Service `migration` (SQLite -> MariaDB).

## Persistenz und Volumes

- `/data` (lokale SQLite, solange SQLite aktiv ist)
- `/data/backups` (Backup-Dateien, restore-faehig)
- `/data/uploads` (Attachment-Dateien)
- MariaDB eigenes Datenvolume (z. B. `/var/lib/mysql`)

## Runtime-Umgebungsvariablen (Soll)

Aktuell aktiv:

- `ND_HUB_DB_PATH` (SQLite-Dateipfad, z. B. `/data/nd_hub_backend.db`)
- `ND_HUB_BACKEND_HOST` (container intern `0.0.0.0`)
- `ND_HUB_BACKEND_PORT` (default `8000`)
- `ND_HUB_INITIAL_ADMIN_PASSWORD`
- `ND_HUB_AUTO_BACKUP_HOURS`

Fuer Migration vorbereiten:

- `ND_HUB_DB_ENGINE` (`sqlite` oder `mariadb`)
- `ND_HUB_MARIADB_HOST`
- `ND_HUB_MARIADB_PORT`
- `ND_HUB_MARIADB_DATABASE`
- `ND_HUB_MARIADB_USER`
- `ND_HUB_MARIADB_PASSWORD`

## Healthchecks

- `ndhub-web`: `GET /health` muss `200` liefern.
- `mariadb`: nativer DB-Healthcheck (z. B. `mysqladmin ping`).
- Startreihenfolge ueber service health statt nur container start order.

## Deployment-Profil je Umgebung

- `local`: SQLite erlaubt, schnelle Entwicklung.
- `staging`: MariaDB verpflichtend, Migrationstests aktiv.
- `production`: MariaDB verpflichtend, Backup/Restore-Runbook verpflichtend.

## Nicht-Ziele fuer Sprint 1

- Kein voller HA-Betrieb mit mehreren Backend-Instanzen.
- Keine externe Secrets-Plattform-Integration.
- Keine automatische Online-Migration ohne Wartungsfenster.

## Abnahme fuer Sprint 1

- Zielprofil ist dokumentiert und vom Team als Referenz akzeptiert.
- Alle spaeteren Docker/Migrations-Tickets referenzieren dieses Profil.
