# FAQ

## Allgemein

### Was ist ND-Hub?

ND-Hub ist eine Plattform zur strukturierten Verwaltung von
Notfalldepots, bereitgestellt als Desktop Client und Webanwendung.
Beide teilen denselben fachlichen Kern.

### Welche Version ist aktuell?

Die aktuelle Version ist **v0.42**. Updates werden in den
[Release Notes](../project/03-release-notes.md) dokumentiert.

### Wo finde ich die Stammdaten?

In der Webanwendung unter dem Menue `Depots`, `Praeparate`,
`Zuordnungen`, `Kontakte`. Im Desktop unter Grundeinstellungen mit
gleichnamigen Tabs.

## Bereitstellung

### Brauche ich Docker?

Fuer die Webanwendung ist Docker der empfohlene Bereitstellungsweg.
Der Desktop Client benoetigt kein Docker; er laeuft direkt unter
Windows/Linux/macOS.

### Welche Datenbank soll ich nutzen?

- **Lokal/Desktop**: SQLite.
- **Pilotbetrieb (Web)**: SQLite ist zulaessig.
- **Staging/Production**: MariaDB.

Mehr unter [SQLite vs. MariaDB](../migration-and-sync/01-sqlite-vs-mariadb.md).

### Wie wechsle ich von SQLite zu MariaDB?

Ueber das dokumentierte Cutover-Vorgehen, siehe
[MariaDB-Cutover](../migration-and-sync/02-mariadb-cutover.md).

## Sicherheit

### Wie werden Passwoerter gespeichert?

Mit bcrypt. Standardrichtlinien:
- Erzwungener Passwortwechsel beim Erststart.
- Account-Sperre nach mehrfachen Fehlversuchen.

### Kann sich ein Admin selbst aussperren?

Nein. Der letzte aktive Admin kann nicht herabgestuft oder deaktiviert
werden. Nutzer koennen sich nicht selbst deaktivieren oder ihre eigene
Rolle aendern.

### Werden Aktionen geloggt?

Ja, im Audit-Log. Filterbar ueber `/audit-logs` (admin-only).

## E-Mail

### Werden E-Mails wirklich versendet?

Standardmaessig nein. Im `draft`-Modus wird nur der Verlauf erstellt.
Mit `ND_HUB_EMAIL_DELIVERY_MODE=smtp` und passenden SMTP-Einstellungen
kann live versendet werden.

### Wo sehe ich den Versandstatus?

Im E-Mail-Verlauf (UI/`GET /emails/history`) oder ueber den Eintrag in
der Datenbank (`email_verlauf.versand_status`).

## Backup & Restore

### Wie haeufig wird automatisch gesichert?

Standardmaessig alle 24 Stunden (`ND_HUB_AUTO_BACKUP_HOURS=24`).

### Kann ich ein SQLite-Backup im MariaDB-Modus zurueckspielen?

Nein. Backups sind engine-aware. Ein SQLite-Backup gehoert in einen
SQLite-Modus, ein MariaDB-Backup (`*.mariadb.json`) in den
MariaDB-Modus.

## Sync

### Was ist Hybrid-Sync?

Ein Modus, in dem der Desktop lokal-zuerst arbeitet und Aenderungen mit
dem Web-Backend synchronisiert. Mehr unter
[Hybrid-Sync](../migration-and-sync/03-hybrid-sync.md).

### Was passiert bei Konflikten?

Letzter-Schreiber-gewinnt mit Hinweisen, `delete` schlaegt `update`,
und `create/create` Dubletten werden mit Konflikthinweis abgelehnt.

### Werden PDF-Anhaenge synchronisiert?

In v1 nein. Die Sync-Strecke uebertraegt fachliche Datensaetze, nicht
Binaerdateien.

## Betrieb

### Wie pruefe ich, ob die Webanwendung laeuft?

`curl http://localhost:8000/health` muss HTTP 200 liefern.

### Wo liegen die Daten persistent?

In Docker-Volumes:
- `ndhub_data` (DB im SQLite-Modus, Misc),
- `ndhub_uploads` (PDF-Anhaenge),
- `ndhub_backups` (Backups),
- `ndhub_mariadb_data` (MariaDB-Datenverzeichnis).

### Ist horizontale Skalierung moeglich?

Nicht ohne Aenderung am Token-Store. Aktuell ist der Token-Store
in-memory. Fuer HA wird ein externer Session-Store benoetigt.
