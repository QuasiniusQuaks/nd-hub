# Glossar

Einheitliche Begrifflichkeiten zur Vermeidung von Missverstaendnissen.

## A

**Acceptance-Suite**: Quality-Gate-Sammlung von Backend-Tests
(`test_stability_acceptance.py` u. a.). Stand: `28 passed`.

**API-Audit-Log**: Persistente Tabelle (`api_audit_log`) mit
Zeit/Akteur/Aktion/Resource fuer fachliche Aktionen.

**Auto-Backup**: Periodisch erstelltes logisches Backup gemaess
`ND_HUB_AUTO_BACKUP_HOURS`.

## B

**Backup (logisch)**: JSON-Dump der Datenstruktur, engine-aware
(`*.json` fuer SQLite, `*.mariadb.json` fuer MariaDB).

**Bewegung**: Zugang, Abgang oder Vernichtung eines Praeparats in einem
Depot, mit Datum, Charge, Verfallsdatum, Anzahl, Typ und optionalem
PDF-Anhang.

**bcrypt**: Passwort-Hash-Verfahren, das ND-Hub fuer Benutzerpasswoerter
einsetzt.

## C

**Cutover (MariaDB)**: Kontrollierter Wechsel des Backends von SQLite
zu MariaDB.

**Cursor (Sync)**: Marker fuer den letzten erfolgreichen Pull;
ermoeglicht inkrementelles Synchronisieren.

## D

**DAL (Data Access Layer)**: Routerklasse im Desktop-Client, die je
nach Modus lokal oder remote arbeitet.

**Depot**: Notfalldepot mit Stammdaten, Kontakten, zugeordneten
Praeparaten und Bewegungen.

**Desktop Client**: PySide6-Anwendung von ND-Hub.

**Dual-Write**: Zeitbefristeter Modus, in dem Writes parallel auf
SQLite und MariaDB landen.

## E

**Engine-Switch**: Umschaltung zwischen SQLite und MariaDB ueber
`ND_HUB_DB_ENGINE`.

**E-Mail Draft**: Mailentwurf, der ohne SMTP-Liveversand im Verlauf
landet.

## F

**Fingerprint (Import)**: Hashbasierter Idempotenzschluessel, der
verhindert, dass derselbe Import doppelt durchgefuehrt wird.

## H

**Health-Endpoint**: `GET /health` liefert HTTP 200 als
Verfuegbarkeitssignal.

**Hybrid-Sync**: Kombinierter lokal-zentraler Betrieb. Lokal-zuerst,
mit Push/Pull bei verfuegbarem Backend.

## I

**Idempotenz**: Eigenschaft von Operationen, dass mehrfache Ausfuehrung
das gleiche Ergebnis liefert.

**Institution**: Traegerorganisation eines oder mehrerer Depots.

## J

**JSON-Dump**: Backup-Format von ND-Hub.

## L

**local_only**: Desktop-Modus, der ausschliesslich lokal arbeitet.

**Lease (Write-Lease)**: Lokales Schreib-Lease im Desktop, schuetzt
gegen parallele Schreibkonflikte.

## M

**MariaDB**: Relationale Datenbank, im Compose-Stack als Service
`mariadb` (Image `mariadb:11.4`).

**Matrix-Report**: Auswertung als Kreuztabelle (z. B. Depots vs.
Praeparate).

## N

**ND-Hub**: Plattformprodukt fuer Notfalldepots; bestehend aus
Desktop Client und Webanwendung.

## O

**Outbox (Sync)**: Lokale Tabelle im Desktop, die ausgehende
Aenderungen vor Push puffert.

## P

**Praeparat**: Stammsatz fuer ein Arzneimittel/Produkt, das in Depots
gefuehrt werden kann.

**Pre-Restore-Snapshot**: automatisch erstelltes Backup unmittelbar vor
einem Restore.

## R

**Remote-only**: Desktop-Modus, der Schreibvorgaenge nur online erlaubt.

**Restore**: Wiederherstellen eines Datenstands aus einem Backup.

**Ranking-Report**: Auswertung mit absteigender Sortierung nach
Kennzahlen.

## S

**Setup-Wizard**: gefuehrte Erstkonfiguration im Desktop Client.

**SMTP-Liveversand**: tatsaechlicher Mailversand ueber SMTP, gegenueber
reinem Draft-Modus.

**Smoke-Test**: Kurzer Funktionscheck nach Deployments oder Cutovern.

**SQLite**: Lokale, dateibasierte Datenbank, die Desktop und (optional)
Web nutzen koennen.

**Sync-Push/Pull**: Sync-Aktionen mit dem Web-Backend.

## T

**Token (Bearer)**: Authentifizierungsformat in der API.

**Tombstone**: Markierung geloeschter Datensaetze fuer Sync-Zwecke
(`deleted_at`).

## U

**Uvicorn**: ASGI-Server fuer FastAPI.

## V

**Verfall**: Verfallsdatum eines Praeparats in einer bestimmten
Charge/Bewegung.

**Volume (Docker)**: Persistenter Speicher fuer den Container-Stack
(z. B. `ndhub_data`, `ndhub_uploads`).

## W

**Web-MVP**: Statisches HTML/CSS/JS-Frontend, das das ND-Hub-Backend
seit der ersten Iteration ausliefert.

**WAL (SQLite)**: Write-Ahead-Logging-Modus fuer bessere Concurrency.
