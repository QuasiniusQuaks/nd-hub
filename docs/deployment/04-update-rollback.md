# Update & Rollback

Diese Seite beschreibt den geregelten Updateprozess fuer den
Webanwendungs-Stack inklusive Rollback-Pfad.

## Vorbereitung

1. Wartungsfenster planen und kommunizieren.
2. Backup erstellen (manuell oder per Auto-Backup verifiziert).
3. Releasenotes/Changelog der neuen Version pruefen.
4. Pruefen, ob `.env` neue Variablen erwartet
   (siehe [Umgebungsvariablen](03-environment-variables.md)).

## Update-Ablauf

### 1) Code aktualisieren

```bash
cd /pfad/zum/repo
git fetch
git checkout <neue-version>
```

### 2) Image neu bauen bzw. Registry-Image ziehen und Stack starten

**Lokaler Build (ohne `NDHUB_WEB_IMAGE`):**

```bash
cd ndhub-web
docker compose pull
docker compose up -d --build
```

**Vorgefertigtes Web-Image (`NDHUB_WEB_IMAGE` in `.env`):**

```bash
cd ndhub-web
docker compose pull ndhub-web
docker compose up -d --no-build
```

### 3) Nach dem Update verifizieren

```bash
docker compose ps
docker compose logs -f ndhub-web
```

Smoke-Pruefung:

- `GET /health` liefert HTTP `200`.
- Login funktioniert.
- Bewegungen, Reports, Backup-Liste reagieren ohne Fehler.

### 4) Optional: spezielle Migrationen

- **Schemaaenderungen** werden ueblicherweise automatisch beim Start
  durch `ensure_schema()` ergaenzt; im MariaDB-Modus laufen die
  passenden Repository-Routinen.
- **Bei groesseren Datenmigrationen** zuvor in Staging spielen, dort
  Smoke-Test ausfuehren, anschliessend produktiv ausrollen.

## Rollback

### Standard-Rollback

```bash
cd ndhub-web
git checkout <vorherige-version>
docker compose up -d --build
```

Anschliessend Smoke-Test wie oben.

### DB-Rollback nach MariaDB-Cutover

Wenn nach einem MariaDB-Cutover Probleme auftreten:

1. `ND_HUB_DB_ENGINE=sqlite` setzen.
2. Stack neu starten.
3. Falls noetig, SQLite aus letztem Backup wiederherstellen.
4. Incident dokumentieren und Ursache analysieren.

Detaillierter Pfad: [MariaDB-Cutover](../migration-and-sync/02-mariadb-cutover.md).

## Risiken minimieren

- Niemals ohne aktuelles Backup updaten.
- Bei Aenderungen an `.env` immer komplett neu erzeugen
  (`docker compose up -d --build`).
- Vor jedem groesseren Update Schreibzugriffe kurz pausieren
  (Read-only-Fenster), damit kein Datenverlust durch In-flight-Writes
  entsteht.
- Update-Schritte einzeln und protokollierbar ausfuehren.

## Audit und Nachweis

- Aenderungen am Stack werden im Changelog/Repository nachgehalten.
- Erfolgreiche Smoke-Tests werden im Betriebsjournal dokumentiert.
- Backup- und Restore-Tests werden mindestens einmal pro Quartal
  protokolliert.
