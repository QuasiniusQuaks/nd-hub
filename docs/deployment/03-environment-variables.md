# Umgebungsvariablen

Vollstaendige Referenz aller `ND_HUB_*`-Variablen, die das Backend und der
Container-Stack auswerten. Quellen: `ndhub-web/backend/README.md`,
`ndhub-web/.env.example`, `ndhub-web/docker-compose.yml`,
`ndhub-web/backend/config.py`.

## Sicherheit und Initialbetrieb

| Variable | Bedeutung | Default |
|---|---|---|
| `ND_HUB_INITIAL_ADMIN_PASSWORD` | Initialpasswort fuer den `admin`-User. | (Beispielwert in `.env.example`) |
| `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC` | Setzt `admin`-Passwort beim Start auf `ND_HUB_INITIAL_ADMIN_PASSWORD` zurueck. Nur temporaer verwenden. | `0` |
| `ND_HUB_AUTO_BACKUP_HOURS` | Intervall fuer automatische Backups. | `24` |
| `ND_HUB_MAX_BACKUP_RESTORE_MB` | Maximalgroesse fuer Restore-Uploads (MB). | `200` |

## Datenpfade und Netzwerk

| Variable | Bedeutung | Default |
|---|---|---|
| `ND_HUB_DB_PATH` | Pfad zur SQLite-Datei (relevant im SQLite-Modus oder Dual-Write). | `/data/nd_hub_backend.db` |
| `ND_HUB_ATTACHMENTS_DIR` | Verzeichnis fuer PDF-Anhaenge. | `/data/uploads` |
| `ND_HUB_BACKUPS_DIR` | Verzeichnis fuer Backups. | `/data/backups` |
| `ND_HUB_BACKEND_HOST` | Bind-Host fuer uvicorn. | `127.0.0.1` (lokal) / `0.0.0.0` (Container) |
| `ND_HUB_BACKEND_PORT` | Bind-Port fuer uvicorn. | `8000` |

## DB-Engine und MariaDB

| Variable | Bedeutung | Default |
|---|---|---|
| `ND_HUB_DB_ENGINE` | `sqlite` oder `mariadb`. | `sqlite` (lokal) / `mariadb` (Compose) |
| `ND_HUB_MARIADB_HOST` | MariaDB-Host. | `mariadb` (Compose-Servicename) |
| `ND_HUB_MARIADB_PORT` | MariaDB-Port. | `3306` |
| `ND_HUB_MARIADB_DATABASE` | Datenbankname. | `ndhub` |
| `ND_HUB_MARIADB_USER` | DB-Benutzer. | `ndhub` |
| `ND_HUB_MARIADB_PASSWORD` | DB-Passwort. | `ChangeMe` (in Production zwingend ersetzen) |
| `ND_HUB_MARIADB_ROOT_PASSWORD` | Root-Passwort fuer den MariaDB-Container. | `ChangeRootMe` |
| `ND_HUB_DUAL_WRITE_SQLITE` | `1` aktiviert Mirror-Writes auf SQLite-Fallback waehrend Cutover. Standard nach Go-Live: `0`. | `0` |

## Feature-Flags

| Variable | Bedeutung | Default |
|---|---|---|
| `ND_HUB_FEATURE_MULTI_INSTITUTION` | Aktiviert Multi-Institution-Funktionen. | `1` (Compose) |
| `ND_HUB_FEATURE_INSTITUTION_MAP` | Aktiviert Karten-Endpunkt `/map/institutions`. | `1` (Compose) |

## E-Mail / SMTP

| Variable | Bedeutung | Default |
|---|---|---|
| `ND_HUB_EMAIL_DELIVERY_MODE` | `draft` (nur Verlauf) oder `smtp` (Liveversand). | `draft` |
| `ND_HUB_SMTP_HOST` | SMTP-Host. | leer |
| `ND_HUB_SMTP_PORT` | SMTP-Port. | `587` |
| `ND_HUB_SMTP_USERNAME` | SMTP-Benutzer. | leer |
| `ND_HUB_SMTP_PASSWORD` | SMTP-Passwort. | leer |
| `ND_HUB_SMTP_USE_TLS` | TLS aktivieren. | `1` |
| `ND_HUB_SMTP_USE_SSL` | SSL aktivieren. | `0` |
| `ND_HUB_SMTP_FROM_ADDRESS` | Absenderadresse. | leer |
| `ND_HUB_SMTP_FROM_NAME` | Absendername. | `ND-Hub` |
| `ND_HUB_SMTP_TIMEOUT_SECONDS` | Timeout fuer SMTP-Verbindung. | `10` |

## Beispiel `.env`

```env
ND_HUB_INITIAL_ADMIN_PASSWORD=ChangeMeToAStrongPassword_123!
ND_HUB_FORCE_ADMIN_PASSWORD_SYNC=0
ND_HUB_AUTO_BACKUP_HOURS=24
ND_HUB_MAX_BACKUP_RESTORE_MB=200

ND_HUB_DB_PATH=/data/nd_hub_backend.db
ND_HUB_ATTACHMENTS_DIR=/data/uploads
ND_HUB_BACKUPS_DIR=/data/backups
ND_HUB_BACKEND_HOST=0.0.0.0
ND_HUB_BACKEND_PORT=8000

ND_HUB_DB_ENGINE=mariadb
ND_HUB_MARIADB_HOST=mariadb
ND_HUB_MARIADB_PORT=3306
ND_HUB_MARIADB_DATABASE=ndhub
ND_HUB_MARIADB_USER=ndhub
ND_HUB_MARIADB_PASSWORD=ChangeMe
ND_HUB_MARIADB_ROOT_PASSWORD=ChangeRootMe
ND_HUB_DUAL_WRITE_SQLITE=0

ND_HUB_FEATURE_MULTI_INSTITUTION=1
ND_HUB_FEATURE_INSTITUTION_MAP=1

ND_HUB_EMAIL_DELIVERY_MODE=draft
ND_HUB_SMTP_HOST=
ND_HUB_SMTP_PORT=587
ND_HUB_SMTP_USERNAME=
ND_HUB_SMTP_PASSWORD=
ND_HUB_SMTP_USE_TLS=1
ND_HUB_SMTP_USE_SSL=0
ND_HUB_SMTP_FROM_ADDRESS=
ND_HUB_SMTP_FROM_NAME=ND-Hub
ND_HUB_SMTP_TIMEOUT_SECONDS=10
```

## Desktop-Konfiguration (Vergleich)

Im Desktop Client erfolgt die Konfiguration in `settings.ini`. Die
wichtigsten Aequivalente sind:

| Web/Backend | Desktop (`settings.ini`) |
|---|---|
| `ND_HUB_DB_PATH` | `database_path` |
| Logging-Level | `log_level` |
| - | `theme` |
| - | `operating_mode` (`local_only` / `hybrid_sync` / `remote_only`) |
| `ND_HUB_BACKEND_*` | `backend_url`, `backend_token` |

Details siehe [Desktop / Konfiguration](../desktop-client/03-configuration.md).
