# Desktop Client: Funktionen

Diese Seite beschreibt die wichtigsten Funktionsbereiche des Desktop
Clients aus Anwendersicht. Die zugehoerigen UI-Seiten und ihre Pfade
finden sich unter [UI-Seiten](05-ui-pages.md).

## Stammdatenverwaltung

- **Depots**: Anlegen, Bearbeiten, Loeschen mit Adress- und
  Geo-Informationen, Zuordnung zu einer Institution.
- **Praeparate**: Stammsatz mit Wirkstoff, Darreichungsform, Staerke,
  Einheit, PZN, Hersteller.
- **Zuordnungen**: pro Depot festlegen, welche Praeparate in welcher
  Sollmenge gefuehrt werden.
- **Kontakte**: Ansprechpartner pro Depot, inkl. E-Mail und Telefon.

## Bewegungen

- Erfassen von **Zugaengen**, **Abgaengen** und **Vernichtungen**.
- Pflichtfelder: Depot, Praeparat, Datum, Charge, Verfall, Anzahl, Typ.
- Optional: Empfaenger, PDF-Anhang.
- Dateivalidierung (PDF, max. 10 MB).
- Direktes Aufrufen einer Detail-/Verfallansicht aus der Bewegung.

## Bewegungs-Verlauf

- Filter nach Typ, Depot, Praeparat, Datum, mit/ohne Anhang, Volltext.
- Persistente Filterauswahl pro Benutzer, Reset-Funktion.
- Pagination und konsistente Sortierung.
- CSV-Export der gefilterten Sicht.
- Direkte PDF-Voransicht aus dem Verlauf.

## Verfall

- Uebersichtsansicht mit Kategorisierung (z. B. abgelaufen, in Kuerze
  ablaufend).
- Detailansicht pro Eintrag mit Bezug zur urspruenglichen Bewegung.
- Export in CSV.
- Polling-Notifications zur fruehzeitigen Warnung.

## Reporting und Auswertungen

- Analytics Control Center mit Tabs: Bestand, Bewegungen, Verfall, Compliance, Szenarien.
- Interaktive Heatmap (Soll/Ist) mit lesbarer Top-N-Darstellung und Hover-Tooltips.
- **Szenarien:** gefuehrte Auswertungen per Dropdown (Depot/Praeparat/Typ/Zeitraum), ohne SQL.
- Auto-Refresh beim Tab-Wechsel; responsive Breite am Viewport.
- Export in CSV, PDF, PPTX (kontextreiche Dateinamen) wo vorgesehen.
- Datumsvalidierung zur Vermeidung inkonsistenter Zeitraeume.

## E-Mail-Workflows

- Empfaengervorschau pro Depot auf Basis der Kontaktstammdaten.
- Erstellen von Drafts mit Vorlagen.
- Optional: Live-Versand ueber konfigurierten SMTP.
- Versandstatus pro Mail (Draft, gesendet, Fehler) mit Verlauf.
- **Report-Schedule:** geplante Analytics-Reports (daily/weekly/monthly, PDF/HTML) unter E-Mail.

## Import

- Import von Bewegungen via CSV/XLS(X).
- Pflichtspalten: `Depot`, `Praeparat`, `Typ`, `Charge`, `Verfall`,
  `Datum`, `Anzahl`. Optional: `Empfaenger`.
- Vorschau mit Fehlerklassifizierung (`error_summary.by_code`).
- Idempotente Ausfuehrung (`import_fingerprint`).
- Optional Dry-Run (`dry_run=true`).

## Benutzer- und Rechteverwaltung

- Benutzer anlegen, bearbeiten, deaktivieren, freigeben.
- Avatar pro Benutzer (Upload/Anzeige).
- Rolle: Admin oder Fachanwender.
- Selbstschutz: kein Selbstdeaktivieren oder Selbst-Rolle-Wechseln; der
  letzte aktive Admin kann nicht herabgestuft werden.
- Optional: feingranulare Lese-/Schreibrechte je Depot.

## Audit-Logs

- Eigener Tab unter Grundeinstellungen.
- Filter nach Aktion, Resource-Typ, Volltext.
- Pagination und Detailansicht.

## Backup und Restore

- Manuelle Backups jederzeit moeglich.
- Auto-Backup-Intervall ueber Konfiguration.
- Restore mit Format- und Groessenpruefung.
- Pre-Restore-Snapshot wird automatisch erstellt.

## Setup-Wizard

- Gefuehrte Erstkonfiguration, inklusive Datenpfad, Betriebsmodus,
  initialer Admin-Benutzer und optionaler Stammdaten.
- Fortschritt persistent gespeichert (`setup_wizard_*`-Settings).

## Hybrid-Sync

- Lokale Outbox fuer Aenderungen im `hybrid_sync`-Modus.
- Push-/Pull-Mechanik mit `batch_id` (Idempotenz) und Cursor.
- Konfliktbehandlung gemaess Sync-Contract v1.

## Fehlerhandling und Logging

- Globaler Exception-Hook faengt nicht behandelte Fehler ab und zeigt
  einen aussagekraeftigen Dialog.
- Logs liegen unter `~/.ND-Hub/logs/`.
- Log-Level konfigurierbar (`log_level` in `settings.ini`).
