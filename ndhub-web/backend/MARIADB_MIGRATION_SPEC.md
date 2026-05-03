# MariaDB Migration Specification (Sprint 1)

Dieses Dokument beschreibt die fachneutrale Migration von SQLite auf MariaDB fuer
`ndhub-web`.

## Migrationsziele

- Keine fachliche Regression gegen Desktop-/Web-Paritaet.
- Datenkonsistenz fuer alle Kernentitaeten.
- Kontrollierter Cutover mit Rollback-Moeglichkeit.

## Scope Entitaeten

- `users`, `user_permissions`, `auth_activity`
- `depots`, `praeparate`, `depot_praeparate`
- `kontakte`
- `bewegungen` (inkl. Attachment-Metadaten)
- `emails_history`
- `audit_logs`
- `meldungs_tracking` / verfall-relevante Daten

## Technische Leitlinien

- API-Vertrag bleibt stabil; nur Storage-Implementierung wechselt.
- SQL-Dialektunterschiede werden in der Repository-Schicht gekapselt.
- IDs bleiben numerisch konsistent.
- Timestamps in UTC speichern.

## SQLite -> MariaDB Mapping (Richtlinie)

- `INTEGER PRIMARY KEY AUTOINCREMENT` -> `BIGINT AUTO_INCREMENT PRIMARY KEY`
- `TEXT` -> `VARCHAR(n)` oder `TEXT` je Feldsemantik
- `REAL` -> `DOUBLE`
- Boolesche Felder -> `TINYINT(1)`
- Datumsfelder (`YYYY-MM-DD`) als `DATE` oder normiertes `VARCHAR(10)` nach Feld
- Zeitstempel als `DATETIME` (UTC)

## Migrationsablauf (Staging/Prod)

1. **Pre-Checks**
   - Quell-DB konsistent (keine defekten FK-Referenzen in fachkritischen Tabellen)
   - Vollstaendiges Backup der SQLite-Datei
2. **Schema Provisioning**
   - MariaDB-Schema erstellen
   - Indizes/Constraints anlegen
3. **Datenuebernahme**
   - Tabellen in definierter Reihenfolge laden
   - FK-sensitive Reihenfolge einhalten
4. **Post-Migration Checks**
   - Row Counts je Tabelle vergleichen
   - Stichproben fuer Reports und Verfallberechnungen
   - Login und zentrale CRUD-Flows testen
5. **Cutover**
   - Backend auf `ND_HUB_DB_ENGINE=mariadb` umstellen
   - Smoke-Test ausfuehren
6. **Rollback (wenn noetig)**
   - Backend zurueck auf SQLite
   - Ursache analysieren, Migration nicht teilweise offen lassen

## Konsistenzpruefungen (Muss)

- Tabellenanzahl SQLite == MariaDB fuer Kernentitaeten
- Summenpruefungen:
  - Anzahl Bewegungen je Typ
  - Anzahl Datensaetze je Depot
  - Anzahl kritischer Verfall-Treffer
- Spot-Checks:
  - mind. 20 Bewegungen inklusive Attachment-Metadaten
  - mind. 10 User-/Permission-Datensaetze
  - mind. 10 Audit-Log-Ereignisse

## Risiken

- SQL-Dialektabweichungen (insb. Upsert/Date-Funktionen)
- Fehlende oder abweichende Indizes mit Performanceeinbruch
- Zeichensatz-/Collation-Abweichungen

## Deliverables der Migrationsphase

- lauffaehiges MariaDB-Schema
- automatisierbares Migrationsskript
- Cutover-Runbook
- dokumentierte Konsistenz- und Smoke-Test-Ergebnisse

## Konkrete Sprint-3 Artefakte

- Migrationsskript: `backend/tools/migrate_sqlite_to_mariadb.py`
- Cutover-Runbook: `backend/MARIADB_CUTOVER_RUNBOOK.md`
- Smoke-Checklist: `backend/MARIADB_SMOKE_CHECKLIST.md`
