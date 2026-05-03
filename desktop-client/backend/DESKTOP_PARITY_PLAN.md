# Desktop-to-Web Parity Plan (1:1)

Dieses Dokument definiert die Umsetzungsregel: Web/Server orientiert sich 1:1 am
bestehenden Desktop-Verhalten, inklusive Validierungen und Datenfluss.

## Paritätsprinzip

- Gleiches Fachverhalten vor neuem UX-Umfang.
- Server validiert dieselben Regeln wie Desktop.
- Web nutzt dieselben Filter-/Flow-Schritte wie Desktop.
- Neue Features erst nach Paritätsabdeckung.

## Funktionsbereiche aus dem Desktop-Client

1. Bewegungen (`page_bewegungen.py`)
   - Typ-spezifische Felder (Zugang/Abgang/Vernichtung)
   - Präparate pro Depot-Zuordnung
   - PDF-Anhang pro Bewegung
2. Verlauf (`page_historie.py`)
   - Filter: Depot, Typ, Volltext
   - PDF öffnen / Ordner öffnen
3. Import (`page_import.py`)
   - CSV/Excel-Import mit Preview
   - Validierung + Fehlermeldungen
   - Excel-Vorlage mit Dropdowns
4. E-Mail (`page_email.py`)
   - Empfänger je Depot/Kontakte
   - Verlauf + Detailansicht
5. Auswertungen (`page_auswertungen.py`)
   - Bewegungsanalyse, Bestand, Ranking, Matrix, Verfall
   - Export PDF/PPT
6. Grundeinstellungen (`page_grundeinstellungen/*`)
   - Depots/Praeparate/Kontakte/Zuordnungen
   - Backup/Restore + Auto-Backup
   - Benutzerverwaltung

## Aktueller Paritätsstand (Web/Server)

- Erreicht:
  - Login/Rollen, Stammdaten CRUD, Bewegungen erfassen
  - Historie-Basics (Liste, Suche, Paging)
  - Admin-Audit-Log inkl. Filter
  - Depot->Präparate-Zuordnung beim Erfassen (1:1 Regel)
- Offen:
  - PDF-Anhänge an Bewegungen
  - Historie: PDF/Ordner öffnen
  - Import inkl. Vorlagen-Download
  - E-Mail-Flow inkl. Verlauf
  - Auswertungen und Exporte
  - Backup/Restore/Auto-Backup
  - Vollständige Benutzerverwaltung im Web

## Umsetzungsreihenfolge (1:1 priorisiert)

1. Bewegungen + Verlauf vervollständigen (PDF-Anhang, Verlauf-Download/Open)
2. Grundeinstellungen: Zuordnungen + Kontakte im Web
3. Import-Workflow wie Desktop
4. E-Mail-Workflow wie Desktop
5. Backup/Restore-Web-Admin
6. Auswertungen + Exporte

