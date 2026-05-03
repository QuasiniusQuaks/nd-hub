# UI Journeys und Funktionsparitaet

Dieses Dokument bildet die Soll-Funktionsparitaet fuer den React/Vite-Teil ab und dient als Referenz fuer die laufende UI-Neugestaltung.

## Primäre User Journeys

### 1) Tagesstart / Lagebild
- Einstieg ueber `Dashboard`.
- KPI-Sichtung (Depots, Praeparate, Bewegungen, kritisch verfallend).
- Sprung in Folgeaktion: `Bewegungen`, `Verfall`, `Auswertungen`.
- Erwartung: Daten in < 2s sichtbar, klare Priorisierung kritischer Signale.

### 2) Bewegung erfassen
- Navigation `Bewegungen > Erfassen`.
- Pflichtfelder ausfuellen + optional PDF-Anhang.
- Speichern + direktes Feedback.
- Erwartung: robuste Validierung, schnelle Dateneingabe, keine Informationsueberladung.

### 3) Bewegung pruefen / Verlauf
- Navigation `Bewegungen > Verlauf`.
- Filter, Suche, Paging.
- Optional: Attachment ansehen/download, CSV Export.
- Erwartung: konsistentes Filterverhalten und klare Tabellenlesbarkeit.

### 4) Verfall managen
- Navigation `Verfall`.
- Filter nach Perspektive, IDs, Suchbegriff.
- Kritische Positionen identifizieren und weiterverfolgen.
- Erwartung: schnell erfassbare Prioritaet (kritisch/warnung/achtung).

### 5) Import verarbeiten
- Navigation `Import`.
- Datei waehlen, Vorschau laden, Fehler pruefen, optional Dry-Run, Execute.
- Template-Download.
- Erwartung: transparente Statusmeldungen und klare Fehlerfuehrung.

### 6) E-Mail Kommunikation
- Navigation `E-Mail`.
- Empfaenger-Preview, Draft erzeugen, optional Live-Versand.
- Historie + Detailinspektion.
- Erwartung: nachvollziehbarer Versandstatus und sichere Bedienung.

### 7) Reporting
- Navigation `Auswertungen`.
- Filter setzen, Daten laden, KPIs sehen, Exporte nutzen.
- Erwartung: Daten-/KPI-Perspektive eindeutig und performant.

### 8) Administration
- Navigation `Stammdaten`, `Zuordnungen`, `Kontakte`, `Benutzer`, `Audit`, `Backup`, `Konto`.
- CRUD-Operationen + sicherheitsrelevante Aktionen (Passwort, Restore, Unlock).
- Erwartung: klare Aktionshierarchie und sauberes Feedback.

## Funktionsparitaet (Muss erhalten bleiben)

- Auth: Login, Logout, Konto, Passwortwechsel, Avatar.
- Dashboard: KPIs, Aktivitaeten, Verfallsvorschau, Refresh.
- Bewegungen: Create, History, Filter, Paging, Attachment Up/Download, CSV Export.
- Verfall: Filter, Stats, Tabellenansicht.
- Import: Preview, Execute, Dry-Run, Error-Log, Template Download.
- E-Mail: Recipient Preview, Draft/Senden, Historie, Detail.
- Reports: Datenabruf, KPI-Output, CSV/PDF/PPT Export.
- Desktop Sync: Token erzeugen, archivierte/aktive Tokens verwalten, widerrufen.
- Benutzerverwaltung: CRUD, Rollen/Rechte, Unlock/Reset/Delete, Aktivitaetslog.
- Audit: Filter + Pagination + Detailansicht.
- Backup: erstellen, herunterladen, wiederherstellen.
- Stammdaten/Zuordnung/Kontakte: vollstaendige CRUD-Flows.

## UX-Kriterien fuer die neue UI

- Gleiches Farbschema, deutlich modernere Hierarchie/Typografie/Spacing.
- Einheitliche Komponenten fuer Tabs, Tabellen, Status, Buttons, Formulare.
- Klare Primary-Actions pro Screen.
- Konsistente Lade-, Leer- und Fehlerzustaende.
- Bewegte Effekte nur subtil und mit `prefers-reduced-motion` respektiert.
