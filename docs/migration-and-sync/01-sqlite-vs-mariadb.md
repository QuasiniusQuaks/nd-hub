# SQLite vs. MariaDB

ND-Hub unterstuetzt beide Engines mit identischer fachlicher
Funktion. Die Wahl haengt vom Bereitstellungsmodell ab.

## Vergleich

| Kriterium | SQLite | MariaDB |
|---|---|---|
| Bereitstellung | dateibasiert | eigener DB-Server |
| Einsatz | Desktop, lokale Tests, kleine Web-Setups | zentral, Staging und Production |
| Skalierung | bis mittlere Last | besser fuer Mehrbenutzer/-standort |
| Backup | Datei-Dump | logischer Dump `*.mariadb.json` |
| Concurrency | begrenzt (WAL) | hoehere Parallelitaet |
| Ops-Aufwand | minimal | regulaerer DB-Betrieb |

## Schema-Mapping

Die Tabellen sind fachlich identisch, mit kleinen Typanpassungen:

| SQLite | MariaDB |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGINT AUTO_INCREMENT PRIMARY KEY` |
| `TEXT` | `VARCHAR(n)` oder `TEXT` |
| `REAL` | `DOUBLE` |
| Boolean (`0/1`) | `TINYINT(1)` |
| ISO-Datum als `TEXT` | `DATE` oder normiertes `VARCHAR(10)` |
| Zeitstempel | `DATETIME` (UTC) |

Das Backend kapselt SQL-Dialektunterschiede in der Repository-Schicht
(`backend/database.py` vs. `backend/mariadb_repository.py`).

## Engine-Switch

| Variable | Wirkung |
|---|---|
| `ND_HUB_DB_ENGINE=sqlite` | SQLite-Pfad (`ND_HUB_DB_PATH`). |
| `ND_HUB_DB_ENGINE=mariadb` | MariaDB-Repository (Connection per `ND_HUB_MARIADB_*`). |
| `ND_HUB_DUAL_WRITE_SQLITE=1` | Spiegelt Writes in SQLite (Diagnose-/Cutover-Phase). |
| `ND_HUB_DUAL_WRITE_SQLITE=0` | Standardmodus nach Cutover (kein Mirror). |

## Wann welche Engine?

| Szenario | Empfehlung |
|---|---|
| Desktop Client | SQLite (lokal, WAL-optimiert). |
| Lokale Tests / Demos | SQLite. |
| Pilotbetrieb (Web) | SQLite zulaessig, mit Pfad zu MariaDB geplant. |
| Staging | MariaDB (verpflichtend). |
| Production | MariaDB (verpflichtend). |

## Operativer Hinweis

- Backup-/Restore-Endpunkte sind engine-aware:
    - SQLite: `*.json` mit Engine-Marker.
    - MariaDB: `*.mariadb.json` (logische Dumps).
- Migrationsskript: `backend/tools/migrate_sqlite_to_mariadb.py`
  (Details: [MariaDB-Cutover](02-mariadb-cutover.md)).
