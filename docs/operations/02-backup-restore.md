# Backup & Restore

## Grundprinzipien

- Backups werden **logisch** erzeugt (JSON-Strukturen, engine-aware).
- Restore akzeptiert nur passende Dateien:
  - SQLite-Modus: `*.json` (Engine-Marker `sqlite`).
  - MariaDB-Modus: `*.mariadb.json`.
- Restores werden nach Format und Groesse geprueft
  (`ND_HUB_MAX_BACKUP_RESTORE_MB`).
- Vor jedem Restore wird automatisch ein **Pre-Restore-Snapshot**
  angelegt.

## Auto-Backup

- Intervall: `ND_HUB_AUTO_BACKUP_HOURS` (Default `24`).
- Auto-Backups landen im Volume `ndhub_backups` (`/data/backups`).
- Beispiel-Dateinamen: `ndhub_auto_<timestamp>.mariadb.json`.

## Manuelles Backup

- UI: Admin > Backup > "Backup erstellen".
- API: `POST /admin/backup/create` (admin-only).
- Resultat enthaelt Dateinamen und Engine-Marker.

## Liste der Backups

- UI: Admin > Backup > Liste.
- API: `GET /admin/backup/list`.

## Restore

- UI: Datei auswaehlen, Restore-Bestaetigung.
- API: `POST /admin/backup/restore` (Multipart-Upload).
- Schritte intern:
    1. Pre-Restore-Snapshot.
    2. Format-/Engine-Pruefung.
    3. Wiederherstellung der Tabellen.
- Nach Restore: Smoke-Test (Login, CRUD, Reports).

## Mit MariaDB

- Backup-Dateien sind logische Dumps `*.mariadb.json`.
- Restore akzeptiert `*.mariadb.json` oder neutrales `*.json` mit
  Engine-Marker.
- Bei MariaDB-Cutover Backup-Strecke vorab pruefen
  (siehe [Migration & Sync / MariaDB-Cutover](../migration-and-sync/02-mariadb-cutover.md)).

## Testkonzept

- **Quartalsweise** Restore-Test in einer separaten Umgebung.
- **Bei Major-Updates** Restore-Test als Teil der Update-Checklist.
- **Nach jedem Migrationsschritt** Smoke-Test inklusive Bewegungen,
  Reports, Backup-Liste.

## Empfehlungen

- Backups regelmaessig zusaetzlich extern sichern (z. B. S3, NAS).
- Backups versionsweise archivieren, mind. 6 Monate aufbewahren.
- Restore-Prozedur in einem internen Runbook fixieren.
