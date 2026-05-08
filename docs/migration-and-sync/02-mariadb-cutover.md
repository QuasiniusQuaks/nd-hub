# MariaDB-Cutover

Diese Seite beschreibt den kontrollierten Umstieg von SQLite auf MariaDB
fuer `ndhub-web`. Sie konsolidiert das Cutover-Runbook, die
Smoke-Checklist, die Migrationsspezifikation und die Dual-Write
Operations Note.

## Ziele

- Keine fachliche Regression gegenueber Desktop/Web-Paritaet.
- Datenkonsistenz fuer alle Kernentitaeten.
- Kontrollierter Cutover mit Rollback-Moeglichkeit.

## Voraussetzungen

- Docker-Stack laeuft, MariaDB-Profil ist gesund.
- Vollstaendiges SQLite-Backup ist erstellt und verifiziert.
- Migrationsskript wurde im Staging mindestens einmal erfolgreich
  ausgefuehrt.
- `docker ps` und API-Aufrufe funktionieren ohne Berechtigungsfehler.

## Scope der Entitaeten

- `users`, `user_permissions`, `auth_activity`
- `depots`, `praeparate`, `depot_praeparate`
- `kontakte`
- `bewegungen` (inkl. Attachment-Metadaten)
- `emails_history`
- `audit_logs`
- verfall-relevante Tabellen (`meldungs_tracking` u. a.)

## Ablauf

### 1) Pre-Cutover

1. Wartungsfenster kommunizieren.
2. Schreibzugriffe stoppen (kurzes Read-only-Fenster).
3. SQLite-Backup erstellen und separat sichern.
4. MariaDB-Erreichbarkeit verifizieren.

### 2) Migration ausfuehren

```bash
python -m backend.tools.migrate_sqlite_to_mariadb \
       --sqlite /data/nd_hub_backend.db
```

Optional fuer einzelne Tabellen:

```bash
python -m backend.tools.migrate_sqlite_to_mariadb \
       --sqlite /data/nd_hub_backend.db \
       --tables users,user_activity_log
```

Quellanalyse ohne MariaDB-Verbindung:

```bash
python -m backend.tools.migrate_sqlite_to_mariadb \
       --sqlite /data/nd_hub_backend.db --dry-run
```

### 3) Post-Migration Validierung

- Row-Counts pro Tabelle vergleichen (`OK`/`MISMATCH`).
- Stichproben:
    - mind. 20 Bewegungen inkl. Attachment-Metadaten,
    - mind. 10 User-/Permission-Datensaetze,
    - mind. 10 Audit-Log-Eintraege.
- Reports und Verfallberechnungen kurz pruefen.

### 4) Cutover-Aktivierung

1. `.env` setzen:
    - `ND_HUB_DB_ENGINE=mariadb`
    - `ND_HUB_MARIADB_*` korrekt befuellen
    - `ND_HUB_DUAL_WRITE_SQLITE=1` nur fuer kurze Uebergangsphase.
2. Stack neu starten.
3. `GET /health` pruefen (`db_engine`-Feld, HTTP 200).
4. Smoke-Test ausfuehren (siehe unten).
5. Nach erfolgreichem Smoke `ND_HUB_DUAL_WRITE_SQLITE=0` setzen,
   Service neu starten, Kurz-Smoke wiederholen.

### 5) Smoke-Test (Pflicht)

- `GET /health` -> 200.
- Login mit Admin-User funktioniert.
- `GET /depots`, `GET /praeparate`, `GET /bewegungen` liefern Daten.
- Bewegung anlegen und erneut listen.
- Import-Preview mit Testdatei.
- `GET /reports/*` liefern Daten.
- Backup-List/Create/Download funktionieren.
- User-Admin-Flow (list/reset/unlock).

### 6) Rollback

Bei kritischen Problemen:

1. `ND_HUB_DB_ENGINE=sqlite` setzen.
2. Service neu starten.
3. Falls noetig SQLite aus Backup wiederherstellen.
4. Incident dokumentieren und Ursache analysieren.

### 7) Login-Sonderfall (Admin-Hash unbekannt)

- temporaer `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC=1` setzen,
- Service neu starten,
- erfolgreich einloggen,
- anschliessend `ND_HUB_FORCE_ADMIN_PASSWORD_SYNC=0` und Neustart.

## Go-Live Checklist (empfohlen)

- `ND_HUB_DB_ENGINE=mariadb` aktiv.
- `ND_HUB_DUAL_WRITE_SQLITE=0` aktiv.
- MariaDB-Counts steigen bei neuen Buchungen, SQLite bleibt stabil.
- Smoke-Checklist komplett gruen.
- Rollback-Pfad dokumentiert und getestet.

## Dual-Write Operations

`ND_HUB_DUAL_WRITE_SQLITE=1` ist nur ein **temporaerer
Uebergangs- oder Diagnosemodus**, kein Dauerzustand.

Wann sinnvoll:

- kurze Stabilisierungsphase nach Major-Change,
- gezielter Diagnosezeitraum,
- enger Canary-Betrieb (Stunden bis Tage).

Wann **nicht**:

- als Workaround fuer ungeklaerte Produktionsfehler,
- dauerhaft "zur Sicherheit",
- waehrend laufender Datenmigrationen ohne klare Datenhoheit.

Risiken:

- hoehere Latenz bei Schreiboperationen,
- erschwerte Fehlersuche durch zwei Write-Ziele,
- Drift-Risiko bei fehlgeschlagenen Mirror-Writes.

## Konsistenzpruefungen

- Tabellenanzahl SQLite == MariaDB fuer Kernentitaeten.
- Summenpruefungen:
    - Anzahl Bewegungen je Typ,
    - Anzahl Datensaetze je Depot,
    - Anzahl kritischer Verfall-Treffer.
- Spot-Checks gemaess Migrationsspezifikation.

## Risiken

- SQL-Dialektunterschiede (Upsert/Date-Funktionen).
- Indizes-/Performanceabweichungen.
- Zeichensatz-/Collation-Probleme.

Ein bewusstes, dokumentiertes Vorgehen mit Backup, Migration, Smoke und
Rollback minimiert diese Risiken.
