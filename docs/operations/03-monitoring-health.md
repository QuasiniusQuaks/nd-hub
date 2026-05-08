# Monitoring & Health

## Healthchecks

| Komponente | Check |
|---|---|
| `ndhub-web` | `GET /health` (HTTP 200 erwartet) |
| `mariadb` | `healthcheck.sh --connect --innodb_initialized` |
| Container | `docker compose ps` |

`docker-compose.yml` startet `ndhub-web` erst, wenn `mariadb` healthy
ist.

## Empfohlene Monitoring-Signale

- **Verfuegbarkeit**: HTTP-200 auf `/health`.
- **Login-Fehler**: erhoehte Rate von `401`-Antworten.
- **Berechtigungs-Fehler**: erhoehte Rate von `403`-Antworten.
- **Restore-Fehler**: Rueckmeldungen von `/admin/backup/restore`.
- **Import-Fehlerquote**: Anzahl `error_summary.by_code`-Eintraege.
- **Sync-Fehler**: `5xx`-Antworten bei `/sync/*`.
- **Mailing**: Versandstatus-Quote (`versand_status=error`).

## KPI fuer Betrieb

- mittlere Antwortzeit `/dashboard/overview` < 1s.
- p95 `/bewegungen` (mit Filter) < 1.5s in MariaDB-Mode.
- Auto-Backup-Erfolg taeglich (genau ein Auto-Backup pro Intervall).

## Logs

- Container-Logs: `docker compose logs -f ndhub-web`.
- Empfehlung: zentrales Log-System (z. B. journald + syslog
  forward, oder ELK/Loki) anbinden.
- Audit-Logs sind ueber `/audit-logs` (admin) abrufbar; sie ergaenzen
  technische Logs um fachliche Aktionen.

## Alerting (Beispielregeln)

- `/health` 5xx in 3 aufeinanderfolgenden Minuten -> Critical.
- Auto-Backup nicht erfolgt seit `2 * ND_HUB_AUTO_BACKUP_HOURS` ->
  Warning.
- `/admin/backup/restore` 4xx-Quote > 0 ueber laengeren Zeitraum ->
  Warning.
- 401/403-Quote ueber Schwellwert -> Warning (Hinweis auf
  Konfigurations- oder Sicherheitsproblem).

## Capacity / Skalierung

- `ndhub-web` skaliert vertikal stabil; horizontale Skalierung
  erfordert externen Session-Store (siehe Known Constraints in
  [Web/Backend / Ueberblick](../web-application/01-overview.md)).
- MariaDB: Speicher und IOPS abhaengig von Datenmenge und
  Reportingdauer; Volumes `ndhub_mariadb_data` regelmaessig auf
  Wachstum pruefen.
