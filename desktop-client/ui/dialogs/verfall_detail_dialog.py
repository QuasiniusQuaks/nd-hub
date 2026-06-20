"""
VerfallDetailDialog - Detailansicht für verfallende Präparate
Version: 1.0 - Angepasst an bestehendes Verfall-System
"""

import logging

from PySide6 import QtCore, QtGui, QtWidgets

from apple_theme import AppleTheme
from icon_manager import IconManager
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog
from verfallmanager import VerfallManager

logger = logging.getLogger(__name__)


class VerfallDetailDialog(QtWidgets.QDialog):
    """
    Dialog der alle verfallenden Präparate im Detail anzeigt
    """

    def __init__(self, verfallmanager: VerfallManager, parent=None):
        super().__init__(parent)
        self.verfallmanager = verfallmanager

        self.setWindowTitle("Verfallende Präparate - Detailansicht")
        self.setMinimumSize(900, 600)

        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        """Erstellt das User Interface"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header_layout = QtWidgets.QHBoxLayout()

        c = AppleTheme.current_colors()

        title = QtWidgets.QLabel("Verfallende Präparate")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {c['label']};
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Export-Button
        export_btn = QtWidgets.QPushButton("📊 Nach Excel exportieren")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['green']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {c['green']}cc;
            }}
        """)
        export_btn.clicked.connect(self.export_excel)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        # Filter-Bereich
        filter_group = QtWidgets.QGroupBox("Filter")
        filter_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: 600;
                border: 1px solid {c['separator']};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {c['label']};
            }}
        """)
        filter_layout = QtWidgets.QHBoxLayout(filter_group)

        # Kategorie-Filter
        filter_layout.addWidget(QtWidgets.QLabel("Kategorie:"))

        self.kategorie_combo = QtWidgets.QComboBox()
        self.kategorie_combo.addItems([
            "Alle anzeigen",
            "🔴 Nur Kritisch (< 30 Tage)",
            "🟠 Nur Warnung (< 90 Tage)",
            "🟡 Nur Achtung (< 180 Tage)"
        ])
        self.kategorie_combo.currentIndexChanged.connect(self.filter_changed)
        filter_layout.addWidget(self.kategorie_combo)

        filter_layout.addSpacing(20)

        # Such-Feld
        filter_layout.addWidget(QtWidgets.QLabel("Suche:"))

        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Präparat oder Depot suchen...")
        self.search_field.textChanged.connect(self.filter_changed)
        filter_layout.addWidget(self.search_field)

        filter_layout.addStretch()

        # Aktualisieren-Button
        refresh_btn = QtWidgets.QPushButton("Aktualisieren")
        refresh_btn.setIcon(IconManager.get_icon("refresh"))
        refresh_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(refresh_btn)

        layout.addWidget(filter_group)

        # Tabelle
        self.table = QtWidgets.QTableWidget()
        
        # Spaltenanzahl abhängig von PZN-Verfügbarkeit
        has_pzn = self.verfallmanager.has_pzn
        self.table.setColumnCount(8 if has_pzn else 7)
        
        headers = ["Kategorie", "Depot", "Präparat"]
        if has_pzn:
            headers.append("PZN")
        headers.extend(["Menge", "Verfallsdatum", "Tage bis Verfall", "Details"])
        self.table.setHorizontalHeaderLabels(headers)

        # Tabellen-Style
        self.table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {c['separator']};
                border-radius: 8px;
                background-color: {c['bg_secondary']};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {c['bg_tertiary']};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {c['separator']};
                font-weight: 600;
                color: {c['label']};
            }}
        """)

        # Tabellen-Einstellungen
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

        # Statistik-Footer
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setStyleSheet(f"""
            color: {c['secondary_label']};
            font-size: 13px;
            padding: 8px;
        """)
        layout.addWidget(self.stats_label)

        # Button-Bereich
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        close_btn = QtWidgets.QPushButton("Schließen")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['secondary_label']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {c['tertiary_label']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def load_data(self):
        """Lädt die Daten in die Tabelle"""
        try:
            # Hole alle verfallenden Präparate
            self.all_data = self.verfallmanager.getverfallendepraeparate()

            # Wende Filter an
            self.filter_changed()

            logger.info(f"{len(self.all_data)} verfallende Präparate geladen")

        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Fehler",
                f"Fehler beim Laden der Daten:\n{str(e)}"
            )

    def filter_changed(self):
        """Filtert die Tabelle basierend auf den Filtern"""
        # Kategorie-Filter
        kategorie_idx = self.kategorie_combo.currentIndex()
        kategorie_map = {
            0: None,  # Alle
            1: 'kritisch',
            2: 'warnung',
            3: 'achtung'
        }
        kategorie_filter = kategorie_map[kategorie_idx]

        # Such-Filter
        search_text = self.search_field.text().lower()

        # Filtere Daten
        filtered_data = []
        for item in self.all_data:
            # Kategorie-Filter
            if kategorie_filter and item['kategorie'] != kategorie_filter:
                continue

            # Such-Filter
            if search_text:
                searchable = f"{item['praeparat_name']} {item['depot_name']} {item['pzn']}".lower()
                if search_text not in searchable:
                    continue

            filtered_data.append(item)

        # Fülle Tabelle
        self._populate_table(filtered_data)

        # Aktualisiere Statistik
        self._update_stats(filtered_data)

    def _populate_table(self, data):
        """Füllt die Tabelle mit Daten"""
        self.table.setRowCount(0)
        has_pzn = self.verfallmanager.has_pzn
        
        for row_idx, item in enumerate(data):
            self.table.insertRow(row_idx)
            
            col_idx = 0
            
            # Kategorie mit Farbe
            kategorie_item = QtWidgets.QTableWidgetItem()
            if item['kategorie'] == 'kritisch':
                kategorie_item.setText("🔴 Kritisch")
                kategorie_item.setForeground(QtGui.QColor("#dc3545"))
            elif item['kategorie'] == 'warnung':
                kategorie_item.setText("🟠 Warnung")
                kategorie_item.setForeground(QtGui.QColor("#fd7e14"))
            else:
                kategorie_item.setText("🟡 Achtung")
                kategorie_item.setForeground(QtGui.QColor("#ffc107"))
            self.table.setItem(row_idx, col_idx, kategorie_item)
            col_idx += 1
            
            # Depot
            self.table.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(item['depot_name']))
            col_idx += 1
            
            # Präparat
            self.table.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(item['praeparat_name']))
            col_idx += 1
            
            # PZN (nur wenn verfügbar)
            if has_pzn:
                self.table.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(str(item['pzn'])))
                col_idx += 1
            
            # Menge
            menge_item = QtWidgets.QTableWidgetItem(str(item['menge']))
            menge_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(row_idx, col_idx, menge_item)
            col_idx += 1
            
            # Verfallsdatum
            self.table.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(item['verfallsdatum']))
            col_idx += 1
            
            # Tage bis Verfall
            tage_item = QtWidgets.QTableWidgetItem(str(item['tage_bis_verfall']))
            tage_item.setTextAlignment(QtCore.Qt.AlignCenter)
            if item['tage_bis_verfall'] < 30:
                tage_item.setForeground(QtGui.QColor("#dc3545"))
            elif item['tage_bis_verfall'] < 90:
                tage_item.setForeground(QtGui.QColor("#fd7e14"))
            self.table.setItem(row_idx, col_idx, tage_item)
            col_idx += 1
            
            # Aktionen (Button-Widget)
            action_widget = QtWidgets.QWidget()
            action_layout = QtWidgets.QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            
            info_btn = QtWidgets.QPushButton("ℹ️")
            info_btn.setFixedSize(28, 28)
            info_btn.setToolTip("Details anzeigen")
            info_btn.clicked.connect(lambda checked, i=item: self._show_details(i))
            action_layout.addWidget(info_btn)
            action_layout.addStretch()
            
            self.table.setCellWidget(row_idx, col_idx, action_widget)

        # Passe Spaltenbreiten an
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def _update_stats(self, data):
        """Aktualisiert die Statistik-Anzeige"""
        kritisch = sum(1 for item in data if item['kategorie'] == 'kritisch')
        warnung = sum(1 for item in data if item['kategorie'] == 'warnung')
        achtung = sum(1 for item in data if item['kategorie'] == 'achtung')
        gesamt = len(data)

        stats_text = (
            f"Gesamt: {gesamt} | "
            f"🔴 Kritisch: {kritisch} | "
            f"🟠 Warnung: {warnung} | "
            f"🟡 Achtung: {achtung}"
        )

        self.stats_label.setText(stats_text)

    def _show_details(self, item):
        """Zeigt Details zu einem Präparat"""
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Präparat-Details")
        msg.setIcon(QtWidgets.QMessageBox.Information)
        
        details = f"""Präparat: {item['praeparat_name']}
    Depot: {item['depot_name']}
    Menge: {item['menge']}
    Verfallsdatum: {item['verfallsdatum']}
    Tage bis Verfall: {item['tage_bis_verfall']}
    Kategorie: {item['kategorie'].title()}"""
        
        # PZN nur anzeigen wenn vorhanden
        if self.verfallmanager.has_pzn and item.get('pzn'):
            details = f"PZN: {item['pzn']}\n" + details

        msg.setText(details)
        exec_embedded_dialog(self, msg)

    def export_excel(self):
        """Exportiert die aktuell gefilterten Daten nach Excel"""
        try:
            # Datei-Dialog
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Excel-Export",
                "verfallende_praeparate.xlsx",
                "Excel-Dateien (*.xlsx)"
            )

            if not filename:
                return

            # Hole Filter-Kategorie
            kategorie_idx = self.kategorie_combo.currentIndex()
            kategorie_map = {
                0: None,
                1: 'kritisch',
                2: 'warnung',
                3: 'achtung'
            }
            kategorie = kategorie_map[kategorie_idx]

            # Exportiere
            success = self.verfallmanager.export_to_excel(filename, kategorie=kategorie)

            if success:
                QtWidgets.QMessageBox.information(
                    self,
                    "Export erfolgreich",
                    f"Daten wurden exportiert nach:\n{filename}"
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Export fehlgeschlagen",
                    "Fehler beim Export. Prüfe das Log für Details.\n\n"
                    "Hinweis: Für Excel-Export wird pandas benötigt:\n"
                    "pip install pandas openpyxl"
                )

        except Exception as e:
            logger.error(f"Fehler beim Excel-Export: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Fehler",
                f"Fehler beim Export:\n{str(e)}"
            )
