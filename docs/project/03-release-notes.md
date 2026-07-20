# Release Notes

Diese Seite buendelt die Releaseuebersicht von ND-Hub auf den
aktuellen Stand v0.5 (ndhub-web **0.1.1**) und gibt eine Kurzfassung der wesentlichen
Aenderungen.

## v0.5.1 Desktop Hotfix (2026-07-20)

### Desktop-Client Stabilität

- **Startup-Crash behoben:** `MainWindow` initialisiert Database vor SecurityManager (Shared-Connection / Issue #18 Regression) — App startet wieder unter Windows.
- **Passwort-Dialog Segfault (Exit 139):** Embedded-Dialoge entkoppeln den Dialog vom Overlay vor `deleteLater`; Passwort-Feedback asynchron.
- **Setup-Wizard „Später“-Overlay:** Backdrop wird zuverlässig entfernt; Wizard als natives Modal-Fenster ohne Parent-Verdunkelung.
- **Setup-Wizard Mixin-`super()`:** `ChromeMixin.showEvent/closeEvent` rufen `QDialog`-Basismethoden explizit auf (setattr-Mixins ohne MRO).
- **Matplotlib-Theme:** `AppleTheme.setup_matplotlib(None)` importiert pyplot lazy (Analytics-Charts).

### Analytics Control Center UX

- **Responsive Viewport-Breite:** Scroll-Content an Viewport geklemmt; Charts mit begrenztem `sizeHint`; Tabellen mit Stretch statt horizontaler Explosion.
- **Heatmap-Lesbarkeit:** adaptive Schriften, Zellgitter, Colorbar-Label, Top-18-Präparate nach |Ist−Soll|, Hover-Tooltips.
- **Tab-Wechsel Auto-Refresh:** aktiver Tab + Insight-Banner werden beim Wechsel neu geladen.
- **SQL-Tab entfernt** zugunsten geführter Szenarien.
- **Email-Schedule** von Analytics nach **E-Mail → Report-Schedule** verschoben.
- **Neu: Tab „Szenarien“** — individuelle Auswertungen per Dropdown (Depot/Präparat/Typ/Zeitraum), Mehrfachauswahl optional, Ergebnis-Tabelle + Zwischenablage.

### Hinweis Betrieb

- Testdaten-Generator: `desktop-client/populate_nd_hub.py` (schreibt nach `%APPDATA%/ND-Hub/nd_hub.db`).
- Empfohlener Start Windows: `desktop-client/.venv` + `python nd_hub.py` (maximiert, nicht Fullscreen).

## v0.5 (aktuell)

### Highlights

- **Analytics Control Center** — kompletter Umbau des Analyse-Bereichs
  von 1374-Zeilen-Monolith zu modularem Kontrollzentrum (34 Module).
- Insight-Banner mit 4 Smart-Cards + Auto-Insights (3 NL-Bullet-Points).
- 5-Tab-Cluster (Stand Hotfix): Bestand, Bewegungen, Verfall, Compliance, Szenarien.
  Custom-SQL entfernt; Email-Schedule unter E-Mail-Seite.
- Interaktive Charts (Heatmap, RankingBar, ForecastBand) mit Hover-Tooltips
  und Click-to-Drill.
- Cross-Filter: Klick auf Chart-Element filtert alle Tabs.
- Vergleichs-Modus (vs. Vorjahr) + Saved Views + Layout-Persistenz.
- Anomalie-Detection (Z-Score mit Farb-Highlight).
- HTML-Export (self-contained, Chart.js) + PDF-Report (ReportLab, Apple-Health-Style).
- Custom-SQL-Editor mit Saved-Queries-Bibliothek (Security: nur SELECT/WITH).
- Email-Schedule (daily/weekly/monthly, PDF/HTML).

### Architektur

- 16 neue DB-Methoden in `db_manager.py` für Analytics-Queries.
- 3 neue SQLite-Tabellen: `analytics_saved_views`, `analytics_saved_queries`, `analytics_email_schedule`.
- 84 neue Tests (alle grün), ruff clean, 0 SyntaxErrors.
- Alte `page_auswertungen.py` → 15-Zeilen-Shim (rückwärtskompatibel).

### Security (aus Audit-Welle 2, nachgetragen)

- Timing-Attacke auf Web-Passwort-Vergleich behoben (`hmac.compare_digest`).
- CORS + TrustedHost + Security-Header Middleware im FastAPI-Backend.
- Login Rate-Limit / Lockout via slowapi.
- Auth-Worker für Passwort-Verifikation (UI-Thread-Entkopplung).
- 518 ruff-Lint-Errors auf 0 reduziert.

## v0.42

### Highlights

- Vollstaendige Enterprise-Dokumentation als MkDocs-Site
  (diese Site).
- MariaDB-Modus produktiv betreibbar; Engine-Switch via
  `ND_HUB_DB_ENGINE`.
- Hybrid-Sync v1 (Push/Pull/Cursor mit `batch_id`-Idempotenz).
- Stability/Acceptance-Suite mit `28 passed` (Stand
  Sprint-Abschluss).
- E-Mail-Workflows mit Draft-/SMTP-Modus, Versandstatus und Verlauf.

### Funktional

- **Stammdaten**: Depots, Praeparate, Kontakte, Zuordnungen mit
  Suche und Pagination.
- **Bewegungen**: Filter (Typ, Depot, Praeparat, Datum, Anhang,
  Volltext), persistent pro Benutzer; CSV-Export.
- **PDF-Anhaenge**: max. 10 MB, Inline/Download-Routen.
- **Reports**: Bestand, Bewegungen, Ranking, Matrix, Verfall in
  CSV, PDF, PPTX.
- **Imports**: Preview, Fehlerklassifizierung, Idempotenz,
  Dry-Run, Excel-Vorlage.
- **Verfall**: Uebersicht, CSV-Export, Polling-Notifications.

### Plattform

- **Docker Stack**: `ndhub-web` + `mariadb`, Healthchecks, Volumes,
  `depends_on: service_healthy`.
- **Container-Registry**: GitHub Actions baut das Web-Image und pusht nach
  GHCR (`ghcr.io/quasiniusquaks/nd-hub`); optional Docker Hub
  (`docker.io/spypanther/ndhub-web` bei `DOCKERHUB_PUSH=true` und Secrets).
  Compose-Variable `NDHUB_WEB_IMAGE` fuer Betrieb mit Registry-Image.
- **Backup/Restore**: Format-/Groessenpruefung, Pre-Restore-
  Snapshot, Engine-Marker.
- **Sicherheit**: bcrypt, Account-Sperre, Self-Toggle-Schutz,
  letzter-Admin-Schutz, gehaerteter Admin-Backup-/Restore-Pfad.

### Migration

- `backend.tools.migrate_sqlite_to_mariadb` mit Dry-Run und
  Tabellenfilter.
- Cutover-Runbook, Smoke-Checklist, Dual-Write-Operations konsolidiert
  unter [Migration & Sync](../migration-and-sync/02-mariadb-cutover.md).

### Bekannte Grenzen

- In-memory Token-Store (Prozess-grenzen).
- Sync v1 ohne binaere Attachment-Synchronisation.
- Frontend-E2E nicht im Backend-Quality-Gate.

## v0.40 / v0.41

- Einfuehrung MariaDB-Repository und Dual-Write-Modus.
- Erweiterung der Filter und Exporte fuer Bewegungen.
- Stabilisierung Backup-/Restore-Pfade und Pre-Restore-Snapshot.
- Erweiterung der Audit-Log-Filter (Action, Resource-Type,
  Volltext).

## v0.39

- Stand der Desktop-Erweiterung; Refactoring zur API-zentrierten
  Architektur startet.
- Einfuehrung des Setup-Wizards.

## Historie (kompakt)

- v0.36 - Konsolidierung der Desktop-Architektur.
- v0.37 - Einfuehrung Sync-Service-Skelett.
- v0.38 - Reportexporte vereinheitlicht.
- v0.39 - Setup-Wizard und globaler Errorhandler.
- v0.40 - MariaDB-Repository (Beta).
- v0.41 - Dual-Write-Modus, gehaertete Admin-Pfade.
- v0.42 - Enterprise-Doku, Hybrid-Sync v1, Acceptance-Suite-Konsolidierung.
- v0.5 - Analytics Control Center (4 Phasen), Audit-Welle 2 Security-Fixes, 84 neue Tests.
