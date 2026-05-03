# MariaDB Cutover Runbook (Sprint 3)

Dieses Runbook beschreibt den kontrollierten Umstieg von SQLite auf MariaDB.

## Voraussetzungen

- Docker-Stack laeuft und MariaDB-Profil ist gesund.
- Docker-Zugriff ist vorhanden (`docker ps` funktioniert ohne Permission-Fehler).
- Vollstaendiges SQLite-Backup ist erstellt und verifiziert.
- Migrationsskript ist im Staging mindestens einmal erfolgreich gelaufen.

## 1. Pre-Cutover

1. Wartungsfenster kommunizieren.
2. Schreibzugriffe stoppen (kurzes Read-only-Fenster).
3. SQLite Backup erzeugen und separat sichern.
4. Ziel-MariaDB auf Erreichbarkeit pruefen.

## 2. Migration ausfuehren

Beispiel:

```bash
python -m backend.tools.migrate_sqlite_to_mariadb --sqlite /data/nd_hub_backend.db
```

Optional fuer Teilbereiche:

```bash
python -m backend.tools.migrate_sqlite_to_mariadb --sqlite /data/nd_hub_backend.db --tables users,user_activity_log
```

Hinweis fuer Backups im MariaDB-Betrieb:

- Backup-Dateien sind logische Dumps im Format `*.mariadb.json`.
- Restore akzeptiert `*.mariadb.json` bzw. `*.json`.

## 3. Post-Migration Validierung

- Row-count Vergleiche aus Skriptausgabe pruefen (`OK` pro Tabelle).
- Smoke-Test:
  - Login
  - Bewegungen Liste/Create
  - Import Preview
  - Reports Endpunkte
  - Backup-Admin Endpunkte

## 4. Cutover Aktivierung

1. `.env` setzen:
   - `ND_HUB_DB_ENGINE=mariadb`
   - `ND_HUB_MARIADB_*` korrekt konfigurieren
   - `ND_HUB_DUAL_WRITE_SQLITE=1` nur fuer kurze Uebergangsphase (optional)
2. Stack neu starten.
3. `GET /health` pruefen (`db_engine` Feld und HTTP 200).
4. Kernprozesse erneut testen.
5. Nach erfolgreichem Smoke-Test auf produktionsnahe Last:
   - `ND_HUB_DUAL_WRITE_SQLITE=0` setzen
   - Service neu starten
   - Kurz-Smoke erneut ausfuehren (CRUD + Reports + Backup-List)

Wenn Login nach Migration fehlschlaegt (alter Admin-Hash unbekannt):

- temporaer `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC=1` setzen
- Service neu starten (setzt `admin` auf `ND_HUB_INITIAL_ADMIN_PASSWORD`)
- erfolgreich einloggen
- `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC` wieder auf `0` setzen und neu starten

## 5. Rollback

Wenn Kritisches fehlschlaegt:

1. `ND_HUB_DB_ENGINE=sqlite` setzen.
2. Service neu starten.
3. Falls noetig SQLite aus Backup wiederherstellen.
4. Incident dokumentieren und Ursachenanalyse starten.

## 6. Nachbereitung

- Migrationsergebnis und Checks archivieren.
- Offene Punkte als Tickets erfassen.
- Erst nach stabiler Beobachtungsphase produktiv freigeben.

## Go-Live Checklist (empfohlen)

- `ND_HUB_DB_ENGINE=mariadb` aktiv.
- `ND_HUB_DUAL_WRITE_SQLITE=0` aktiv.
- MariaDB-Counts steigen bei neuen Buchungen, SQLite bleibt stabil.
- Smoke-Checklist komplett gruen.
- Rollback-Pfad dokumentiert und getestet.

## Incident-Hinweis

- Der temporare Einsatz von `ND_HUB_DUAL_WRITE_SQLITE=1` erfolgt nur kontrolliert
  gemaess [Dual-Write Operations Note](DUAL_WRITE_OPERATIONS_NOTE.md).
