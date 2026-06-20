"""Import-Funktionalität - Excel/CSV-Datenimport."""
import os
import hashlib
from datetime import datetime

import pandas as pd
HAS_PANDAS = True

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from db_manager import Database
from icon_manager import IconManager
from apple_theme import AppleTheme
from ui.utils import create_card_widget, configure_responsive_table

class ImportPage(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_file = None
        self.preview_data = None
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        page_scroll = QtWidgets.QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout.addWidget(page_scroll)

        content = QtWidgets.QWidget()
        page_scroll.setWidget(content)

        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)
        
        title = QtWidgets.QLabel("Daten-Import")
        title.setProperty("class", "page-title")
        content_layout.addWidget(title)
        
        if not HAS_PANDAS:
            warning = QtWidgets.QLabel(
                "pandas nicht installiert!\n\n"
                "Für den Import benötigen Sie pandas und openpyxl:\n"
                "pip install pandas openpyxl"
            )
            wc = AppleTheme.current_colors()
            warning.setStyleSheet(
                f"background-color: {wc['status_orange_bg']}; padding: 20px; border-radius: 8px; "
                f"color: {wc['status_orange']}; font-size: 14px; border: 1px solid {wc['status_orange']};"
            )
            warning.setWordWrap(True)
            content_layout.addWidget(warning)
            return
        
        tabs = QtWidgets.QTabWidget()
        
        # === TAB: Bewegungen importieren ===
        tab_bewegungen = QtWidgets.QWidget()
        tab_bew_layout = QtWidgets.QVBoxLayout(tab_bewegungen)
        tab_bew_layout.setContentsMargins(0, 0, 0, 0)
        
        bew_card = create_card_widget()
        bew_layout = QtWidgets.QVBoxLayout(bew_card)
        
        info_bew = QtWidgets.QLabel(
            "Importieren Sie Zu- und Abgänge aus CSV/Excel-Dateien.\n"
            "Erforderliche Spalten: Depot, Präparat, Typ, Charge, Verfall, Datum, Anzahl, Empfänger (optional)"
        )
        info_bew.setWordWrap(True)
        self._info_bew_label = info_bew
        self._apply_import_static_label_styles()
        bew_layout.addWidget(info_bew)
        
        file_layout = QtWidgets.QHBoxLayout()
        self.btn_select_bewegungen = QtWidgets.QPushButton(" Datei auswählen")
        self.btn_select_bewegungen.setIcon(IconManager.get_icon("folder"))
        self.btn_select_bewegungen.setObjectName("btn_add")
        self.btn_template_bewegungen = QtWidgets.QPushButton(" Excel-Vorlage herunterladen")
        self.btn_template_bewegungen.setIcon(IconManager.get_icon("file_text"))
        self.btn_template_bewegungen.setObjectName("btn_secondary")
        file_layout.addWidget(self.btn_select_bewegungen)
        file_layout.addWidget(self.btn_template_bewegungen)
        file_layout.addStretch()
        bew_layout.addLayout(file_layout)
        
        self.label_file_bewegungen = QtWidgets.QLabel("Keine Datei ausgewählt")
        bew_layout.addWidget(self.label_file_bewegungen)
        
        self.table_preview_bewegungen = QtWidgets.QTableWidget()
        self.table_preview_bewegungen.setMinimumHeight(220)
        self.table_preview_bewegungen.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        configure_responsive_table(self.table_preview_bewegungen)
        bew_layout.addWidget(QtWidgets.QLabel("Vorschau:"))
        bew_layout.addWidget(self.table_preview_bewegungen)
        
        self.label_status_bewegungen = QtWidgets.QLabel("")
        self.label_status_bewegungen.setStyleSheet("font-weight: 600; margin: 8px 0;")
        bew_layout.addWidget(self.label_status_bewegungen)
        
        self.text_errors_bewegungen = QtWidgets.QTextEdit()
        self.text_errors_bewegungen.setReadOnly(True)
        self.text_errors_bewegungen.setMinimumHeight(80)
        self.text_errors_bewegungen.setMaximumHeight(180)
        self.text_errors_bewegungen.setVisible(False)
        bew_layout.addWidget(self.text_errors_bewegungen)

        self.label_import_fingerprint = QtWidgets.QLabel("")
        bew_layout.addWidget(self.label_import_fingerprint)
        
        import_layout_bew = QtWidgets.QHBoxLayout()
        self.btn_import_bewegungen = QtWidgets.QPushButton("✅ Import starten")
        self.btn_import_bewegungen.setObjectName("btn_save")
        self.btn_import_bewegungen.setMinimumHeight(44)
        self.btn_import_bewegungen.setEnabled(False)
        import_layout_bew.addStretch()
        import_layout_bew.addWidget(self.btn_import_bewegungen)
        bew_layout.addLayout(import_layout_bew)
        
        tab_bew_layout.addWidget(bew_card)
        tabs.addTab(tab_bewegungen, "Bewegungen importieren")
        
        content_layout.addWidget(tabs)
        
        self.btn_select_bewegungen.clicked.connect(self.select_bewegungen_file)
        self.btn_template_bewegungen.clicked.connect(self.download_bewegungen_template)
        self.btn_import_bewegungen.clicked.connect(self.import_bewegungen)
        self._apply_import_file_and_fingerprint_styles()

    def _apply_import_static_label_styles(self) -> None:
        c = AppleTheme.current_colors()
        self._info_bew_label.setStyleSheet(
            f"color: {c['secondary_label']}; font-size: 12px; margin-bottom: 12px;"
        )

    def _apply_import_file_and_fingerprint_styles(self) -> None:
        c = AppleTheme.current_colors()
        self.label_import_fingerprint.setStyleSheet(
            f"font-size: 12px; color: {c['secondary_label']};"
        )
        if self.label_file_bewegungen.text().startswith("📄"):
            self.label_file_bewegungen.setStyleSheet(
                f"color: {c['green']}; font-weight: 600; margin: 8px 0;"
            )
        else:
            self.label_file_bewegungen.setStyleSheet(
                f"color: {c['secondary_label']}; font-style: italic; margin: 8px 0;"
            )

    def refresh_theme(self) -> None:
        self._apply_import_static_label_styles()
        self._apply_import_file_and_fingerprint_styles()
        c = AppleTheme.current_colors()
        t = self.label_status_bewegungen.text()
        if "Fehler" in t:
            self.label_status_bewegungen.setStyleSheet(
                f"color: {c['orange']}; font-weight: 600; margin: 8px 0;"
            )
        elif t.startswith("✅"):
            self.label_status_bewegungen.setStyleSheet(
                f"color: {c['green']}; font-weight: 600; margin: 8px 0;"
            )

    def _toast(self, message: str, level: str = "info"):
        host = self.window()
        if hasattr(host, "show_toast"):
            host.show_toast(message, level)

    def select_bewegungen_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "CSV/Excel-Datei auswählen", "",
            "Alle Dateien (*.csv *.xlsx *.xls);;CSV-Dateien (*.csv);;Excel-Dateien (*.xlsx *.xls)"
        )
        if file_path:
            self.current_file = file_path
            self.label_file_bewegungen.setText(f"📄 {os.path.basename(file_path)}")
            self._apply_import_file_and_fingerprint_styles()
            self.preview_bewegungen_file()

    def preview_bewegungen_file(self):
        try:
            import warnings
            # UserWarning für Data Validation unterdrücken
            warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
            
            # Excel mit skiprows=3 lesen (Anleitung, Depot-Wahl, Header überspringen)
            if self.current_file.endswith('.csv'):
                df = pd.read_csv(self.current_file)
            else:
                df = pd.read_excel(self.current_file, header=2)
            
            # ✅ WICHTIG: Spaltennamen in Strings konvertieren (behebt datetime-Fehler)
            df.columns = df.columns.astype(str).str.strip()
            
            # Leere Zeilen entfernen
            df = df.dropna(how='all')
            
            # Spalten-Mapping (akzeptiert verschiedene Schreibweisen)
            column_mapping = {
                'depot': ['depot', 'Depot'],
                'präparat': ['präparat', 'Präparat', 'praeparat'],
                'typ': ['typ', 'Typ', 'type'],
                'charge': ['charge', 'Charge'],
                'verfall': ['verfall', 'Verfall', 'verfallsdatum'],
                'datum': ['datum', 'Datum', 'date'],
                'anzahl': ['anzahl', 'Anzahl', 'menge', 'quantity'],
                'empfänger': ['empfänger', 'Empfänger', 'empfaenger']
            }

            # Spaltennamen normalisieren
            normalized_columns = {}
            for standard_name, aliases in column_mapping.items():
                for col in df.columns:
                    if col in aliases:
                        normalized_columns[col] = standard_name
                        break

            # Dataframe umbenennen
            df.rename(columns=normalized_columns, inplace=True)
            
            # Datumsspalten in String konvertieren
            if 'verfall' in df.columns:
                df['verfall'] = df['verfall'].apply(
                    lambda x: pd.to_datetime(x, dayfirst=True).strftime('%d.%m.%Y') if pd.notna(x) else ''
                )
            if 'datum' in df.columns:
                df['datum'] = df['datum'].apply(
                    lambda x: pd.to_datetime(x, dayfirst=True).strftime('%d.%m.%Y') if pd.notna(x) else ''
                )

            # Prüfen ob alle Pflichtfelder vorhanden
            required = ['depot', 'präparat', 'typ', 'charge', 'verfall', 'datum', 'anzahl']
            missing = [c for c in required if c not in df.columns]
            if missing:
                QtWidgets.QMessageBox.critical(
                    self, "Fehler",
                    f"Fehlende Spalten: {', '.join(missing)}\n\n"
                    f"Vorhandene Spalten: {', '.join(df.columns.tolist())}"
                )
                return
            
            preview_df = df.head(10)
            self.table_preview_bewegungen.clear()
            self.table_preview_bewegungen.setColumnCount(len(preview_df.columns))
            self.table_preview_bewegungen.setRowCount(len(preview_df))
            self.table_preview_bewegungen.setHorizontalHeaderLabels(preview_df.columns.tolist())
            
            for r in range(len(preview_df)):
                for c, col in enumerate(preview_df.columns):
                    val = preview_df.iloc[r, c]
                    self.table_preview_bewegungen.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
            
            self.table_preview_bewegungen.resizeColumnsToContents()
            configure_responsive_table(
                self.table_preview_bewegungen,
                content_columns=list(range(self.table_preview_bewegungen.columnCount())),
            )
            
            errors = []
            warnings = []
            seen_keys = set()
            for idx, row in df.iterrows():
                # NaN-Werte abfangen
                if pd.isna(row.get('depot')) or pd.isna(row.get('präparat')):
                    continue
                    
                depot_name = str(row['depot']).strip()
                praeparat_name = str(row['präparat']).strip()
                typ = str(row['typ']).strip()
                anzahl = row['anzahl']
                
                if not depot_name or depot_name == 'nan':
                    continue
                
                if not self.db.get_depot_id_by_name(depot_name):
                    errors.append(f"Zeile {idx+5}: Depot '{depot_name}' nicht gefunden")
                
                if not self.db.get_praeparat_id_by_name(praeparat_name):
                    errors.append(f"Zeile {idx+5}: Präparat '{praeparat_name}' nicht gefunden")
                
                if typ not in ['Zugang', 'Abgang', 'Vernichtung']:
                    errors.append(f"Zeile {idx+5}: Ungültiger Typ '{typ}'")
                
                try:
                    if pd.isna(anzahl) or int(anzahl) <= 0:
                        errors.append(f"Zeile {idx+5}: Anzahl muss > 0 sein")
                except (ValueError, TypeError):
                    errors.append(f"Zeile {idx+5}: Ungültige Anzahl '{anzahl}'")

                key = (
                    str(row.get('depot', '')).strip().lower(),
                    str(row.get('präparat', '')).strip().lower(),
                    str(row.get('typ', '')).strip().lower(),
                    str(row.get('charge', '')).strip().lower(),
                    str(row.get('datum', '')).strip().lower(),
                    str(row.get('anzahl', '')).strip().lower(),
                )
                if key in seen_keys:
                    warnings.append(f"Zeile {idx+5}: Möglicher Duplikat-Eintrag")
                else:
                    seen_keys.add(key)
            
            # Leere Zeilen entfernen
            df = df[df['depot'].notna() & (df['depot'].astype(str).str.strip() != '')]
            
            self.preview_data = df
            preview_fingerprint = hashlib.sha256(
                ("|".join(df.columns.tolist()) + "|" + str(len(df)) + "|" + str(df.head(30).to_dict())).encode("utf-8")
            ).hexdigest()[:16]
            self.label_import_fingerprint.setText(
                f"Import-Fingerprint: {preview_fingerprint} | Duplikat-Warnungen: {len(warnings)}"
            )
            
            if errors:
                self.label_status_bewegungen.setText(f"{len(df)} Zeilen gefunden, {len(errors)} Fehler")
                oc = AppleTheme.current_colors()
                self.label_status_bewegungen.setStyleSheet(
                    f"color: {oc['orange']}; font-weight: 600; margin: 8px 0;"
                )
                self.text_errors_bewegungen.setPlainText("\n".join(errors[:20]))
                self.text_errors_bewegungen.setVisible(True)
                self.btn_import_bewegungen.setEnabled(len(errors) < len(df))
            else:
                self.label_status_bewegungen.setText(f"✅ {len(df)} Zeilen bereit zum Import")
                oc = AppleTheme.current_colors()
                self.label_status_bewegungen.setStyleSheet(
                    f"color: {oc['green']}; font-weight: 600; margin: 8px 0;"
                )
                if warnings:
                    self.text_errors_bewegungen.setPlainText("\n".join(warnings[:20]))
                    self.text_errors_bewegungen.setVisible(True)
                else:
                    self.text_errors_bewegungen.setVisible(False)
                self.btn_import_bewegungen.setEnabled(True)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QtWidgets.QMessageBox.critical(
                self, "Fehler", 
                f"Datei konnte nicht gelesen werden:\n{str(e)}"
            )
            self.btn_import_bewegungen.setEnabled(False)

    def import_bewegungen(self):
        if self.preview_data is None:
            return
        
        reply = QtWidgets.QMessageBox.question(
            self, "Import bestätigen",
            f"Möchten Sie {len(self.preview_data)} Bewegungen importieren?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply != QtWidgets.QMessageBox.Yes:
            return
        
        progress = QtWidgets.QProgressDialog("Importiere Daten...", "Abbrechen", 0, len(self.preview_data), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        imported = 0
        errors = []
        
        for idx, row in self.preview_data.iterrows():
            if progress.wasCanceled():
                break
            
            progress.setValue(idx)
            
            try:
                depot_id = self.db.get_depot_id_by_name(str(row['depot']).strip())
                praeparat_id = self.db.get_praeparat_id_by_name(str(row['präparat']).strip())
                typ = str(row['typ']).strip()
                charge = str(row['charge']).strip()
                verfall = row['verfall']
                datum = row['datum']
                anzahl = int(row['anzahl'])
                empfaenger = str(row.get('empfänger', '')).strip() if 'empfänger' in row and pd.notna(row.get('empfänger')) else None
                
                if not depot_id or not praeparat_id:
                    errors.append(f"Zeile {idx+5}: Depot oder Präparat nicht gefunden")
                    continue
                
                # Datumskonvertierung mit Fehlerbehandlung
                try:
                    if isinstance(datum, str):
                        datum_obj = pd.to_datetime(datum, dayfirst=True).strftime('%Y-%m-%d')
                    else:
                        datum_obj = pd.to_datetime(datum).strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    datum_obj = str(datum)
                
                try:
                    if isinstance(verfall, str):
                        verfall_obj = pd.to_datetime(verfall, dayfirst=True).strftime('%Y-%m-%d')
                    else:
                        verfall_obj = pd.to_datetime(verfall).strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    verfall_obj = str(verfall)
                
                eingang = datum_obj if typ == 'Zugang' else None
                ausgang = datum_obj if typ in ('Abgang', 'Vernichtung') else None
                
                self.db.insert_bewegung(
                    depot_id, praeparat_id, charge, verfall_obj,
                    eingang, ausgang, empfaenger, anzahl, typ
                )
                imported += 1
                
            except Exception as e:
                errors.append(f"Zeile {idx+5}: {str(e)}")
        
        progress.setValue(len(self.preview_data))
        
        msg = f"✅ {imported} Bewegungen erfolgreich importiert!"
        if errors:
            msg += f"\n\n{len(errors)} Fehler:\n" + "\n".join(errors[:10])
        
        QtWidgets.QMessageBox.information(self, "Import abgeschlossen", msg)
        if imported > 0:
            level = "warning" if errors else "success"
            suffix = f", {len(errors)} Fehler" if errors else ""
            self._toast(f"Import abgeschlossen: {imported} Bewegungen{suffix}.", level)
        
        self.current_file = None
        self.preview_data = None
        self.label_file_bewegungen.setText("Keine Datei ausgewählt")
        self._apply_import_file_and_fingerprint_styles()
        self.table_preview_bewegungen.clear()
        self.label_status_bewegungen.setText("")
        self.label_import_fingerprint.setText("")
        self.btn_import_bewegungen.setEnabled(False)
    
    def download_bewegungen_template(self):
        """Erstellt eine Excel-Vorlage mit Dropdown-Listen und Depot-Auswahl"""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Excel-Vorlage speichern", "bewegungen_vorlage.xlsx",
            "Excel-Dateien (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            from openpyxl import Workbook
            from openpyxl.worksheet.datavalidation import DataValidation
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            
            # Workbook erstellen
            wb = Workbook()
            ws = wb.active
            ws.title = "Bewegungen"
            
            # Daten abrufen
            depots = [d[1] for d in self.db.list_depots()]
            praeparate = [p[1] for p in self.db.list_praeparate()]
            typen = ["Zugang", "Abgang", "Vernichtung"]
            
            # === Validierungsblatt erstellen (ausgeblendet) ===
            validation_sheet = wb.create_sheet("Validierung")
            
            # Depots in Spalte A
            for idx, depot in enumerate(depots, 1):
                validation_sheet[f'A{idx}'] = depot
            
            # Präparate in Spalte B
            for idx, praeparat in enumerate(praeparate, 1):
                validation_sheet[f'B{idx}'] = praeparat
            
            # Typen in Spalte C
            for idx, typ in enumerate(typen, 1):
                validation_sheet[f'C{idx}'] = typ
            
            # Validierungsblatt ausblenden
            validation_sheet.sheet_state = 'hidden'
            
            # === ZEILE 1: Erklärung ===
            ws.merge_cells('A1:H1')
            ws['A1'] = (
                "Anleitung: Wählen Sie unten (Zeile 2) einmalig das Depot aus. "
                "Dieses Depot wird automatisch für alle Zeilen übernommen. "
                "Füllen Sie dann die weiteren Spalten aus. "
                "HINWEIS: Empfänger nur bei 'Abgang' ausfüllen, bei Zugang/Vernichtung leer lassen!"
            )
            ws['A1'].font = Font(size=11, color="856404", italic=True)
            ws['A1'].alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
            ws['A1'].fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
            ws.row_dimensions[1].height = 45
            
            # === ZEILE 2: Depot-Auswahl ===
            ws.merge_cells('A2:A2')
            ws['A2'] = "→ Depot für ALLE Zeilen:"
            ws['A2'].font = Font(bold=True, size=12, color="003366")
            ws['A2'].alignment = Alignment(vertical="center")
            
            # Depot-Dropdown in B2 (Verweis auf Validierungsblatt)
            depot_range = f"Validierung!$A$1:$A${len(depots)}"
            dv_depot_header = DataValidation(type="list", formula1=depot_range, allow_blank=False)
            dv_depot_header.prompt = "Depot auswählen"
            dv_depot_header.promptTitle = "Depot-Auswahl"
            dv_depot_header.error = "Bitte wählen Sie ein Depot aus der Liste"
            dv_depot_header.errorTitle = "Ungültige Eingabe"
            ws.add_data_validation(dv_depot_header)
            dv_depot_header.add('B2')
            ws['B2'].fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
            ws['B2'].font = Font(bold=True, size=11)
            
            ws.merge_cells('C2:H2')
            ws['C2'] = "← Bitte hier Depot auswählen, dann automatisch für alle Zeilen übernommen"
            ws['C2'].font = Font(italic=True, color="7f8c8d", size=10)
            ws['C2'].alignment = Alignment(vertical="center")
            
            # === ZEILE 3: Spaltenüberschriften ===
            headers = ["Depot", "Präparat", "Typ", "Charge", "Verfall", "Datum", "Anzahl", "Empfänger"]
            header_fill = PatternFill(start_color="34495e", end_color="34495e", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=12)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col_num)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # === ZEILE 4-103: Datenzeilen (100 Zeilen) ===
            for row in range(4, 104):
                # Spalte A: Depot - nur anzeigen wenn Präparat ausgefüllt ist
                ws.cell(row=row, column=1).value = f'=IF(B{row}<>"",$B$2,"")'
                ws.cell(row=row, column=1).font = Font(color="003366")
                ws.cell(row=row, column=1).fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
                
                # Spalte E (Verfall - Datum kurz: DD.MM.YYYY)
                verfall_cell = ws.cell(row=row, column=5)
                verfall_cell.number_format = 'DD.MM.YYYY'
                
                # Spalte F (Datum - Datum kurz: DD.MM.YYYY)
                datum_cell = ws.cell(row=row, column=6)
                datum_cell.number_format = 'DD.MM.YYYY'
            
            # Dropdown für Präparate (Spalte B, Zeilen 4-103)
            praeparat_range = f"Validierung!$B$1:$B${len(praeparate)}"
            dv_praeparat = DataValidation(type="list", formula1=praeparat_range, allow_blank=False)
            dv_praeparat.prompt = "Präparat auswählen"
            dv_praeparat.promptTitle = "Präparat-Liste"
            dv_praeparat.error = "Bitte wählen Sie ein Präparat aus der Liste"
            dv_praeparat.errorTitle = "Ungültige Eingabe"
            ws.add_data_validation(dv_praeparat)
            dv_praeparat.add('B4:B103')
            
            # Dropdown für Typ (Spalte C, Zeilen 4-103)
            typ_range = f"Validierung!$C$1:$C${len(typen)}"
            dv_typ = DataValidation(type="list", formula1=typ_range, allow_blank=False)
            dv_typ.prompt = "Typ auswählen: Zugang, Abgang oder Vernichtung"
            dv_typ.promptTitle = "Typ-Liste"
            dv_typ.error = "Bitte wählen Sie einen Typ aus: Zugang, Abgang, Vernichtung"
            dv_typ.errorTitle = "Ungültige Eingabe"
            ws.add_data_validation(dv_typ)
            dv_typ.add('C4:C103')
            
            # === ZEILE 4: Beispieldaten ===
            if depots and praeparate:
                ws['B2'].value = depots[0]  # Beispiel-Depot vorauswählen
                example_row = [
                    '',  # Depot kommt aus Formel
                    praeparate[0],
                    "Zugang",
                    "CH12345",
                    "31.12.2026",  # DD.MM.YYYY Format
                    datetime.now().strftime("%d.%m.%Y"),  # DD.MM.YYYY Format
                    "10",
                    ""  # Empfänger leer bei Zugang
                ]
                for col_num, value in enumerate(example_row, 1):
                    if col_num > 1:  # Depot überspringen (kommt aus Formel)
                        cell = ws.cell(row=4, column=col_num)
                        cell.value = value
                        # Datum-Format: DD.MM.YYYY
                        if col_num in [5, 6]:  # Verfall und Datum
                            cell.number_format = 'DD.MM.YYYY'
            
            # Spaltenbreiten anpassen
            column_widths = [22, 26, 16, 15, 15, 15, 10, 28]
            for i, width in enumerate(column_widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = width
            
            # Zeilenhöhen
            ws.row_dimensions[2].height = 25
            ws.row_dimensions[3].height = 25
            
            # Speichern
            wb.save(file_path)
            
            QtWidgets.QMessageBox.information(
                self, 
                "✅ Excel-Vorlage erstellt", 
                f"Vorlage erfolgreich gespeichert:\n{file_path}\n\n"
                "Die Vorlage enthält:\n"
                "• Anleitung in Zeile 1\n"
                "• Depot-Auswahl in Zeile 2 (wird automatisch übernommen)\n"
                "• Depot erscheint nur in Zeilen mit Präparat\n"
                "• Dropdown-Listen für Präparat und Typ\n"
                "• Datums-Spalten (Verfall & Datum) im Format DD.MM.YYYY\n"
                "• Beispielzeile zum Verständnis\n\n"
                "WICHTIG: Empfänger nur bei 'Abgang' ausfüllen!"
            )
            self._toast("Excel-Vorlage erfolgreich erstellt.", "success")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                "Fehler", 
                f"Excel-Vorlage konnte nicht erstellt werden:\n{str(e)}"
            )


