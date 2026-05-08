# Umgebungen

ND-Hub wird in unterschiedlichen Profilen betrieben. Diese Seite gibt eine
einheitliche Empfehlung pro Umgebung. Die zugehoerigen
Variablenbelegungen finden sich auf
[Umgebungsvariablen](03-environment-variables.md).

## Profile

### Local

- Zweck: Entwicklung, Tests, Demo.
- Datenbank: SQLite zulaessig.
- E-Mail: `draft`-Modus.
- Backups: optional.
- Healthchecks: nicht zwingend extern beobachtet.

### Staging

- Zweck: Migrations- und Abnahmetests, Vorbereitung Go-Live.
- Datenbank: MariaDB **verpflichtend**.
- Migrationsskripte werden hier zuerst geprueft.
- Backup/Restore-Tests muessen erfolgreich durchgefuehrt werden.

### Production

- Zweck: Produktivbetrieb fuer Kunden.
- Datenbank: MariaDB **verpflichtend**.
- Backup/Restore-Runbook **verpflichtend** (siehe
  [Operations / Backup & Restore](../operations/02-backup-restore.md)).
- Monitoring/Alerting auf Healthchecks und Errorquoten erforderlich.
- Reverse Proxy mit TLS-Terminierung empfohlen.

## Empfohlene Variablenwerte je Profil

| Variable | Local | Staging | Production |
|---|---|---|---|
| `ND_HUB_DB_ENGINE` | `sqlite` | `mariadb` | `mariadb` |
| `ND_HUB_DUAL_WRITE_SQLITE` | `0` | `0` (nur Cutover befristet `1`) | `0` |
| `ND_HUB_AUTO_BACKUP_HOURS` | `24` | `24` | `12-24` |
| `ND_HUB_MAX_BACKUP_RESTORE_MB` | `200` | `200` | `200`+ je Datenvolumen |
| `ND_HUB_EMAIL_DELIVERY_MODE` | `draft` | `draft` oder `smtp` | bewusst dokumentiert |
| `ND_HUB_BACKEND_HOST` | `0.0.0.0` (Container) | `0.0.0.0` | `0.0.0.0` |
| `ND_HUB_BACKEND_PORT` | `8000` | `8000` | `8000` (intern) |

## Empfehlungen

- Reverse Proxy (z. B. Nginx, Traefik) als TLS-Terminator vor
  `ndhub-web` schalten.
- Secrets nicht in Repository-Konfigurationen halten; produktiv ueber
  Secret-Stores oder docker secrets versorgen.
- Logging zentralisieren (z. B. journald, ELK, Loki).
- Healthchecks per Monitoring (Uptime + `/health`) ueberwachen.
