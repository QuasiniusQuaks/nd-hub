# Migration & Sync

Diese Sektion deckt zwei zentrale Themen fuer ND-Hub ab:

1. die **Datenbankstrategie** (SQLite und MariaDB) inkl. produktivem
   MariaDB-Cutover und
2. den **Hybrid-Sync** zwischen Desktop Client und Web-Backend.

## Inhalt

- [SQLite vs. MariaDB](01-sqlite-vs-mariadb.md) - wann welche Engine
  und wie sie sich auf den Betrieb auswirkt.
- [MariaDB-Cutover](02-mariadb-cutover.md) - vollstaendiger Cutover-,
  Smoke- und Rollback-Pfad.
- [Hybrid-Sync](03-hybrid-sync.md) - Sync-Contract v1 mit
  Betriebsmodi `local_only`, `hybrid_sync`, `remote_only`.
