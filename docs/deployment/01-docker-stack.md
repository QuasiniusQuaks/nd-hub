# Docker-Stack

Diese Seite beschreibt den **tatsaechlichen aktuellen Deployment-Stand**
der Webanwendung mit Docker (v0.42).

## Topologie

Der Stack besteht aus zwei Services und persistenten Volumes:

```mermaid
flowchart LR
    subgraph composeStack["docker compose stack"]
        ndhubWeb["ndhub-web (FastAPI)\nPort 8000"]
        mariadb["mariadb 11.4\nPort 3306"]
    end
    ndhubWeb -->|depends_on healthy| mariadb
    ndhubWeb --> volData["Volume ndhub_data"]
    ndhubWeb --> volUploads["Volume ndhub_uploads"]
    ndhubWeb --> volBackups["Volume ndhub_backups"]
    mariadb --> volMaria["Volume ndhub_mariadb_data"]
```

## Services

### `ndhub-web`

| Eigenschaft | Wert |
|---|---|
| Image | gebaut aus `ndhub-web/Dockerfile` |
| Basis | `python:3.12-slim` (Frontend-Stage `node:20-slim`) |
| Port | `8000` |
| Healthcheck | `GET /health` (intern via `urllib`) |
| Restart | `unless-stopped` |
| Default-Engine | `ND_HUB_DB_ENGINE=mariadb` |

### `mariadb`

| Eigenschaft | Wert |
|---|---|
| Image | `mariadb:11.4` |
| Port | `3306` |
| Healthcheck | `healthcheck.sh --connect --innodb_initialized` |
| Volume | `ndhub_mariadb_data:/var/lib/mysql` |

## Voraussetzungen

- Docker Engine + Docker Compose Plugin installiert.
- Port `8000` und (bei externer DB-Nutzung) `3306` verfuegbar.
- Fuer produktionsnahe Umgebungen: gepflegte `.env` mit sicheren Secrets.

## Konfiguration vorbereiten

```bash
cd ndhub-web
cp .env.example .env
```

Wichtige Variablen siehe [Umgebungsvariablen](03-environment-variables.md).

## Deployment starten

```bash
cd ndhub-web
docker compose up -d --build
```

Nach erfolgreichem Start verfuegbar:

- App/API: `http://localhost:8000`
- Health: `http://localhost:8000/health`

## Betriebsmodi

### MariaDB-Modus (empfohlen fuer Staging/Production)

- `.env`: `ND_HUB_DB_ENGINE=mariadb`
- Compose startet `mariadb` automatisch mit.
- `depends_on: condition: service_healthy` stellt sicher, dass
  `ndhub-web` erst nach DB-Healthcheck startet.

### SQLite-Modus (lokaler/test-Betrieb)

- `.env`: `ND_HUB_DB_ENGINE=sqlite`
- Backend nutzt `ND_HUB_DB_PATH=/data/nd_hub_backend.db`.
- Der Stack enthaelt weiterhin den MariaDB-Service; fachlich nutzt das
  Backend in diesem Modus aber SQLite.

## Healthchecks und Verifikation

```bash
cd ndhub-web
docker compose ps
docker compose logs -f ndhub-web
```

Minimalpruefung nach Deploy:

- `GET /health` liefert HTTP `200`.
- Login funktioniert.
- Kernflows (Bewegungen, Reports, Backup-Liste) ohne Fehler.

## Persistenz

| Volume | Inhalt |
|---|---|
| `ndhub_data` | SQLite-Datei (im SQLite-Modus) und kleinere Datenartefakte. |
| `ndhub_uploads` | PDF-Anhaenge der Bewegungen. |
| `ndhub_backups` | Backups (logisch, JSON oder MariaDB-Dumps). |
| `ndhub_mariadb_data` | Datenverzeichnis von MariaDB. |

## Update- und Restart-Operationen

```bash
cd ndhub-web
docker compose pull
docker compose up -d --build
docker compose restart ndhub-web
```

Hinweis: Bei Aenderungen an `.env` oder Dependencies den Stack neu
erzeugen (`up -d --build`).

## Backup, Restore und Betriebssicherheit

- Persistente Daten liegen in Volumes (DB, Uploads, Backups).
- Backup/Restore-Endpunkte sind gehaertet (Format-/Groessenpruefung).
- Engine-aware Backup-Dateinamen:
  - SQLite: `*.json` mit Engine-Marker.
  - MariaDB: `*.mariadb.json` (logischer JSON-Dump).
- Fuer MariaDB-Cutover und produktive Freigabe siehe
  [Migration & Sync / MariaDB-Cutover](../migration-and-sync/02-mariadb-cutover.md).

## Produktionsnahe Mindest-Checkliste

- Starke Passwoerter/Secrets in `.env`.
- `ND_HUB_DB_ENGINE=mariadb` fuer zentrale Umgebung aktiv.
- `ND_HUB_DUAL_WRITE_SQLITE=0` ausserhalb kontrollierter
  Uebergangsfenster.
- Healthchecks gruen, Smoketests bestanden.
- Backup-Restore-Test einmal in Zielumgebung validiert.
- E-Mail-Betrieb bewusst dokumentiert (`draft` oder `smtp`).

## Beispiel `docker-compose.yml` (Auszug)

```yaml
services:
  ndhub-web:
    build: .
    container_name: ndhub-web
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      mariadb:
        condition: service_healthy
    volumes:
      - ndhub_data:/data
      - ndhub_uploads:/data/uploads
      - ndhub_backups:/data/backups
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

  mariadb:
    image: mariadb:11.4
    container_name: ndhub-mariadb
    restart: unless-stopped
    volumes:
      - ndhub_mariadb_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]

volumes:
  ndhub_data:
  ndhub_uploads:
  ndhub_backups:
  ndhub_mariadb_data:
```
