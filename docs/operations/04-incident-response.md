# Incident Response

## Reaktionsstufen

| Severity | Beispiel | Reaktion |
|---|---|---|
| SEV-1 | App nicht erreichbar; massive Datenverluste | sofort, 24/7 |
| SEV-2 | wichtige Funktion ausgefallen (z. B. Login) | innerhalb Geschaeftszeit prioritaer |
| SEV-3 | Beeintraechtigung ohne Datenverlust (z. B. langsame Reports) | regulaer geplant |

## Erste Schritte (Triage)

1. Healthcheck pruefen: `curl http://localhost:8000/health`.
2. Containerstatus pruefen: `docker compose ps`.
3. Logs sichten: `docker compose logs --tail=200 ndhub-web mariadb`.
4. Symptom konkretisieren:
    - 5xx-Quote? -> Backend-/DB-Stoerung.
    - 4xx-Quote? -> AuthN/AuthZ-/Konfigurationsproblem.
    - Healthcheck rot, Login funktioniert nicht? -> Tokens (in-memory)
      koennten nach Neustart unwirksam sein. Erneut anmelden.

## Kritische Stoerungsbilder

### Backend startet nicht

- Pruefe `.env` und Pflichtvariablen
  (`ND_HUB_DB_ENGINE`, `ND_HUB_MARIADB_*`, `ND_HUB_INITIAL_ADMIN_PASSWORD`).
- Pruefe ob Volumes vollgelaufen sind.
- Konsultiere Logs.

### MariaDB nicht erreichbar

- `docker compose ps` zeigt `mariadb` als unhealthy.
- Pruefe Volumes und Speicher.
- Bei Cutover-Problemen: temporaerer Rollback auf SQLite
  (siehe [Migration & Sync / MariaDB-Cutover](../migration-and-sync/02-mariadb-cutover.md)).

### Datenintegritaet zweifelhaft

- Vor jeder Aktion: Backup ziehen.
- Letzten konsistenten Stand identifizieren (Audit-Logs, letzte
  erfolgreiche Backups).
- Restore in eine separate Test-Umgebung, fachliche Pruefung,
  anschliessend kontrolliert produktiv anwenden.

### SMTP-Versand schlaegt fehl

- Versandstatus im E-Mail-Verlauf pruefen
  (`versand_status=error`, `versand_fehler`).
- SMTP-Konfiguration validieren.
- Bei laengeren Stoerungen auf `ND_HUB_EMAIL_DELIVERY_MODE=draft`
  zuruecksetzen.

## Rollback-Pfade

- **App-Update zurueckdrehen**: `git checkout <vorherige-version>` +
  `docker compose up -d --build`.
- **DB-Engine-Rollback**: `ND_HUB_DB_ENGINE=sqlite` setzen, ggf.
  SQLite aus Backup wiederherstellen.
- **Datenwiederherstellung**: `POST /admin/backup/restore` mit
  validierter Backup-Datei.

## Kommunikation

- Stakeholder fruehzeitig informieren (intern/extern, je nach
  Severity).
- Statusupdate mindestens stuendlich bei SEV-1/2.
- Nach Behebung: Postmortem mit Ursache, Massnahmen, Lessons Learned.

## Postmortem-Vorlage (Kurzform)

| Punkt | Inhalt |
|---|---|
| Zeitachse | Eintritt, Erkennung, Behebung |
| Auswirkung | Welche Funktion war wie lange gestoert? |
| Ursache | technisch + organisatorisch |
| Massnahmen | Sofort + nachhaltig |
| Owner | Verantwortliche pro Massnahme |
| Status | offen / in Umsetzung / abgeschlossen |
