!!! warning "Archiviert"
    Diese Originaldatei ist archiviert. Der aktuelle, konsolidierte Stand befindet sich in der Enterprise-Dokumentation (siehe Hauptnavigation links).

# MariaDB Smoke Checklist (Sprint 3)

Nach Migration und vor Cutover-Freigabe:

- `GET /health` liefert `200`.
- Login mit Admin-User funktioniert.
- `GET /depots`, `GET /praeparate`, `GET /bewegungen` liefern Daten.
- Bewegung anlegen und erneut listen.
- Import-Preview mit Testdatei ausfuehren.
- Report-Endpunkte (`/reports/*`) liefern Daten.
- Backup-List/Create/Download funktionieren.
- User-Admin-Flow (list/reset/unlock) ist funktionsfaehig.

Bei Fehlern: Cutover abbrechen und Rollback gemaess `MARIADB_CUTOVER_RUNBOOK.md`.
