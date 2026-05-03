"""Auswertungen & Analytics - Diagramme und Statistiken."""
import os
import logging
import textwrap
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, QDate

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from db_manager import Database, to_iso
from icon_manager import IconManager
from apple_theme import AppleTheme
from responsive_widgets import ResponsiveWidget, FlowLayout, AnalyticsKpiCard, ModernChartContainer
from ui.utils import create_card_widget, NumericTableWidgetItem, configure_responsive_table
from ui.dialogs.dialog_ppt_export import PPTExportDialog
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog

# Qt-Dateidialog: unter Linux/Portal wirkt der native Dialog oft „losgelöst“ und das Hauptfenster verschwindet hinter dem Busy-Overlay.
_QT_SAVE_OPTIONS = QtWidgets.QFileDialog.Option.DontUseNativeDialog


class AuswertungenPage(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db

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

        # Titel
        title = QtWidgets.QLabel("Auswertungen & Analysen")
        title.setProperty("class", "page-title")
        content_layout.addWidget(title)

        # Haupt-Layout: Filter links, Ergebnisse rechts
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setSpacing(20)

        # === LINKE SEITE: FILTER ===
        filter_card = create_card_widget()
        filter_card.setMinimumWidth(260)
        filter_card.setMaximumWidth(340)
        filter_layout = QtWidgets.QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(20, 20, 20, 20)
        filter_layout.setSpacing(15)

        filter_title = QtWidgets.QLabel("Analytics Filter")
        filter_title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {AppleTheme.current_colors()['label']}; margin-bottom: 5px;")
        filter_layout.addWidget(filter_title)

        # Perspektive wählen
        perspective_group = QtWidgets.QGroupBox("Perspektive")
        perspective_layout = QtWidgets.QVBoxLayout(perspective_group)
        self.radio_depot = QtWidgets.QRadioButton(" Pro ND-Hub Depot(s)")
        self.radio_praeparat = QtWidgets.QRadioButton(" Pro Präparat(e)")
        self.radio_depot.setChecked(True)
        self.radio_depot.toggled.connect(self.on_perspective_changed)
        self.radio_praeparat.toggled.connect(self.on_perspective_changed)
        perspective_layout.addWidget(self.radio_depot)
        perspective_layout.addWidget(self.radio_praeparat)
        filter_layout.addWidget(perspective_group)

        # Auswahl (dynamisch: Depots oder Präparate)
        self.selection_group = QtWidgets.QGroupBox("Auswahl")
        self.selection_layout = QtWidgets.QVBoxLayout(self.selection_group)
        self.selection_list = QtWidgets.QListWidget()
        self.selection_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.selection_list.setMinimumHeight(180)
        self.selection_layout.addWidget(self.selection_list)

        select_all_btn = QtWidgets.QPushButton("Alle auswählen")
        select_all_btn.setObjectName("btn_secondary")
        select_all_btn.clicked.connect(self.select_all)
        self.selection_layout.addWidget(select_all_btn)

        filter_layout.addWidget(self.selection_group)

        # Zeitraum
        zeitraum_group = QtWidgets.QGroupBox("Zeitraum (optional)")
        zeitraum_layout = QtWidgets.QFormLayout(zeitraum_group)

        self.date_von = QtWidgets.QDateEdit()
        self.date_von.setCalendarPopup(True)
        self.date_von.setDate(QDate.currentDate().addYears(-1))
        self.date_von.setDisplayFormat("dd.MM.yyyy")

        self.date_bis = QtWidgets.QDateEdit()
        self.date_bis.setCalendarPopup(True)
        self.date_bis.setDate(QDate.currentDate())
        self.date_bis.setDisplayFormat("dd.MM.yyyy")

        zeitraum_layout.addRow("Von:", self.date_von)
        zeitraum_layout.addRow("Bis:", self.date_bis)
        filter_layout.addWidget(zeitraum_group)

        # Auswertungstyp
        auswertung_group = QtWidgets.QGroupBox("Auswertungstyp")
        auswertung_layout = QtWidgets.QVBoxLayout(auswertung_group)

        self.btn_bewegungen = QtWidgets.QPushButton(" Bewegungsanalyse")
        self.btn_bewegungen.setIcon(IconManager.get_icon("activity"))
        self.btn_bewegungen.clicked.connect(lambda: self.request_auswertung("bewegungen"))

        self.btn_bestand = QtWidgets.QPushButton(" Bestandsentwicklung")
        self.btn_bestand.setIcon(IconManager.get_icon("bar_chart"))
        self.btn_bestand.clicked.connect(lambda: self.request_auswertung("bestand"))

        self.btn_ranking = QtWidgets.QPushButton(" Ranking")
        self.btn_ranking.setIcon(IconManager.get_icon("award"))
        self.btn_ranking.clicked.connect(lambda: self.request_auswertung("ranking"))

        self.btn_matrix = QtWidgets.QPushButton(" Matrix-Ansicht")
        self.btn_matrix.setIcon(IconManager.get_icon("map"))
        self.btn_matrix.clicked.connect(lambda: self.request_auswertung("matrix"))

        self.btn_verfall = QtWidgets.QPushButton(" Verfalls-Prognose")
        self.btn_verfall.setIcon(IconManager.get_icon("clock"))
        self.btn_verfall.clicked.connect(lambda: self.request_auswertung("verfall"))

        for btn in [self.btn_bewegungen, self.btn_bestand, self.btn_ranking, self.btn_matrix, self.btn_verfall]:
            btn.setMinimumHeight(40)
            auswertung_layout.addWidget(btn)

        filter_layout.addWidget(auswertung_group)
        filter_layout.addStretch()

        main_layout.addWidget(filter_card)

        # === RECHTE SEITE: ERGEBNISSE ===
        self.results_card = create_card_widget()
        results_layout = QtWidgets.QVBoxLayout(self.results_card)

        self.results_title = QtWidgets.QLabel("Wählen Sie eine Auswertung")
        results_layout.addWidget(self.results_title)

        # Scroll-Bereich für Ergebnisse
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.results_widget = QtWidgets.QWidget()
        self.results_layout = QtWidgets.QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(0, 0, 10, 0)
        self.results_layout.setSpacing(20)

        # 🚀 KPI-Leiste (Top Row)
        self.kpi_container = QtWidgets.QWidget()
        self.kpi_layout = FlowLayout(self.kpi_container, margin=0, h_spacing=12, v_spacing=12)
        self.kpi_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.addWidget(self.kpi_container)

        # Bereich für Diagramme & Tabellen
        self.content_container = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)
        self.results_layout.addWidget(self.content_container)

        # 🏗️ Persistent Action Bar (Top of Results)
        self.action_bar = QtWidgets.QWidget()
        self.action_layout = FlowLayout(self.action_bar, margin=0, h_spacing=10, v_spacing=10)
        self.action_layout.setContentsMargins(0, 0, 0, 10)
        
        self.export_report_btn = QtWidgets.QPushButton(" Bericht speichern")
        self.export_report_btn.setIcon(IconManager.get_icon("file_text"))
        self.export_report_btn.setObjectName("btn_secondary")
        self.export_report_btn.clicked.connect(self._handle_export_report_clicked)
        self.action_layout.addWidget(self.export_report_btn)
        
        self.export_charts_btn = QtWidgets.QPushButton(" Diagramme speichern")
        self.export_charts_btn.setIcon(IconManager.get_icon("bar_chart"))
        self.export_charts_btn.setObjectName("btn_add")
        self.export_charts_btn.clicked.connect(self._handle_export_charts_clicked)
        self.action_layout.addWidget(self.export_charts_btn)
        
        self.export_ppt_btn = QtWidgets.QPushButton(" PowerPoint erstellen")
        self.export_ppt_btn.setIcon(IconManager.get_icon("monitor"))
        self.export_ppt_btn.setObjectName("btn_add")
        self.export_ppt_btn.clicked.connect(self._handle_export_ppt_clicked)
        self.action_layout.addWidget(self.export_ppt_btn)
        self._apply_results_title_and_ppt_button_style()
        self._export_report_action = None
        self._export_charts_action = None
        self._export_report_message = "Erstelle Bericht ..."
        self._export_charts_message = "Exportiere Diagramme ..."
        
        self.action_bar.hide() # Initial hidden
        
        results_layout.insertWidget(1, self.action_bar)

        scroll.setWidget(self.results_widget)
        results_layout.addWidget(scroll)

        main_layout.addWidget(self.results_card, 1)

        content_layout.addLayout(main_layout)
        
        # Initial: Depots laden
        self.load_selection_items()
        self.show_empty_state()

    def on_perspective_changed(self, toggled):
        """Wird aufgerufen, wenn zwischen Depot- und Präparate-Ansicht gewechselt wird"""
        if toggled:
            self.load_selection_items()

    def _begin_busy(self, message: str, delay_ms: int = 0) -> int:
        host = self.window()
        if hasattr(host, "_begin_busy_operation"):
            return host._begin_busy_operation(message, delay_ms=delay_ms)
        return -1

    def _end_busy(self, op_id: int) -> None:
        host = self.window()
        if hasattr(host, "_end_busy_operation"):
            host._end_busy_operation(op_id)

    def load_selection_items(self):
        """Lädt Depots oder Präparate in die Liste"""
        self.selection_list.clear()
        
        try:
            if self.radio_depot.isChecked():
                # Depots laden
                items = self.db.list_depots()
                for item_id, name, *rest in items:
                    list_item = QtWidgets.QListWidgetItem(name)
                    list_item.setData(Qt.UserRole, item_id)
                    self.selection_list.addItem(list_item)
                self.selection_group.setTitle(f"Auswahl: Depots ({len(items)})")
            else:
                # Präparate laden
                items = self.db.list_praeparate()
                for item_id, name in items:
                    list_item = QtWidgets.QListWidgetItem(name)
                    list_item.setData(Qt.UserRole, item_id)
                    self.selection_list.addItem(list_item)
                self.selection_group.setTitle(f"Auswahl: Präparate ({len(items)})")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Auswahl-Items: {e}")

    def get_selected_ids(self):
        """Gibt die IDs der markierten Elemente zurück"""
        return [self.selection_list.item(i).data(Qt.UserRole) 
                for i in range(self.selection_list.count()) 
                if self.selection_list.item(i).isSelected()]

    def select_all(self):
        """Wählt alle Elemente in der Liste aus"""
        for i in range(self.selection_list.count()):
            self.selection_list.item(i).setSelected(True)

    def show_empty_state(self):
        """Zeigt einen Hinweis an, wenn noch keine Auswertung gewählt wurde"""
        self.clear_results()
        empty_card = create_card_widget()
        empty_layout = QtWidgets.QVBoxLayout(empty_card)
        empty_layout.setContentsMargins(40, 60, 40, 60)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QtWidgets.QLabel("")
        icon_label.setStyleSheet("font-size: 64px; margin-bottom: 20px;")
        
        hint_label = QtWidgets.QLabel("Wähle links die gewünschten Daten und einen Auswertungstyp aus.")
        hint_label.setStyleSheet(f"font-size: 16px; color: {AppleTheme.current_colors()['secondary_label']}; font-weight: 500;")
        hint_label.setAlignment(Qt.AlignCenter)
        
        empty_layout.addWidget(icon_label, 0, Qt.AlignCenter)
        empty_layout.addWidget(hint_label, 0, Qt.AlignCenter)
        
        self.content_layout.addWidget(empty_card)

    def add_kpi(self, title, value, unit="", color=None):
        """Fügt eine KPI-Karte zur Leiste hinzu"""
        card = AnalyticsKpiCard(title, value, unit, color)
        self.kpi_layout.addWidget(card)

    def clear_results(self):
        """Löscht alle bisherigen Ergebnisse (KPIs und Content)"""
        while self.kpi_layout.count():
            child = self.kpi_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Letzten Typ merken für Theme-Refresh
        self.last_auswertung_typ = None
        self.action_bar.hide()

    def update_action_bar(self, typ, **kwargs):
        """Aktualisiert die Buttons in der Aktionsleiste basierend auf dem Typ"""
        self._export_report_action = None
        self._export_charts_action = None
        self._export_report_message = "Erstelle Bericht ..."
        self._export_charts_message = "Exportiere Diagramme ..."
        self.action_bar.show()
        self.export_ppt_btn.show() # Immer zeigen

        
        if typ == "bewegungen":
            table = kwargs.get('table')
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')
            self._export_report_action = lambda: self.export_bewegungen_tabelle_pdf(table, start_date, end_date)
            self._export_charts_action = lambda: self.export_bewegungen_all_pdf(start_date, end_date)
            self._export_report_message = "Erstelle Bewegungsbericht (PDF) ..."
            self._export_charts_message = "Exportiere Bewegungsdiagramme ..."
            self.export_report_btn.show()
            self.export_charts_btn.show()
        elif typ == "bestand":
            table = kwargs.get('table')
            canvases = kwargs.get('canvases')
            self._export_report_action = lambda: self.export_generic_table_pdf("Bestand", table)
            self._export_charts_action = lambda: self.export_generic_charts_pdf("Bestandsentwicklung", canvases)
            self._export_report_message = "Erstelle Bestandsbericht (PDF) ..."
            self._export_charts_message = "Exportiere Bestandsdiagramme ..."
            self.export_report_btn.show()
            self.export_charts_btn.show()
        elif typ == "ranking":
            table = kwargs.get('table')
            canvases = kwargs.get('canvases')
            self._export_report_action = lambda: self.export_generic_table_pdf("Ranking", table)
            self._export_charts_action = lambda: self.export_generic_charts_pdf("Ranking", canvases)
            self._export_report_message = "Erstelle Ranking-Bericht (PDF) ..."
            self._export_charts_message = "Exportiere Ranking-Diagramme ..."
            self.export_report_btn.show()
            self.export_charts_btn.show()
        elif typ == "matrix":
            canvases = kwargs.get('canvases')
            self.export_report_btn.hide() # Keine Tabelle für Matrix
            self._export_charts_action = lambda: self.export_generic_charts_pdf("Matrix_Bestand", canvases)
            self._export_charts_message = "Exportiere Matrix-Diagramm ..."
            self.export_charts_btn.show()
        elif typ == "verfall":
            canvases = kwargs.get('canvases')
            self.export_report_btn.hide() # Meist nur Chart sinnvoll
            self._export_charts_action = lambda: self.export_generic_charts_pdf("Verfallsprognose", canvases)
            self._export_charts_message = "Exportiere Verfallsprognose ..."
            self.export_charts_btn.show()

    def _run_busy_action(self, message: str, callback) -> None:
        """Zeigt Busy sofort und startet Aktion im nächsten Event-Loop-Tick."""
        busy_op_id = self._begin_busy(message, delay_ms=0)

        def _execute():
            try:
                callback()
            finally:
                self._end_busy(busy_op_id)

        QtCore.QTimer.singleShot(0, _execute)

    def _save_file_path(self, title: str, default_name: str, name_filter: str) -> str:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window(),
            title,
            default_name,
            name_filter,
            "",
            _QT_SAVE_OPTIONS,
        )
        return path or ""

    def _handle_export_report_clicked(self) -> None:
        if self._export_report_action is None:
            return
        # Kein Busy-Overlay vor dem Dateidialog (sonst wirkt das Hauptfenster „weg“).
        self._export_report_action()

    def _handle_export_charts_clicked(self) -> None:
        if self._export_charts_action is None:
            return
        self._export_charts_action()

    def _handle_export_ppt_clicked(self) -> None:
        self.show_ppt_dialog()

    def show_ppt_dialog(self):
        """Öffnet den Konfigurationsdialog für das PowerPoint Management Reporting."""
        selected_depots = []
        if self.radio_depot.isChecked():
            selected_depots = self.get_selected_ids()
            
        dialog = PPTExportDialog(self.db, default_depot_ids=selected_depots, parent=self)
        exec_embedded_dialog(self, dialog)

    def _apply_results_title_and_ppt_button_style(self) -> None:
        c = AppleTheme.current_colors()
        self.results_title.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 12px;"
        )
        if hasattr(self, "export_ppt_btn"):
            self.export_ppt_btn.setStyleSheet(
                f"background-color: {c['purple']}; color: #ffffff; border: none; "
                f"border-radius: 8px; padding: 10px 20px; font-weight: 600;"
            )

    def refresh_theme(self):
        """Aktualisiert die Diagramme bei Theme-Wechsel"""
        self._apply_results_title_and_ppt_button_style()
        if hasattr(self, 'last_auswertung_typ') and self.last_auswertung_typ:
            # Falls bereits eine Auswertung angezeigt wird, diese mit neuem Theme neu laden
            self.request_auswertung(self.last_auswertung_typ)
        else:
            # Ansonsten nur den Empty State (bzw. Titel) aktualisieren
            self.show_empty_state()

    def request_auswertung(self, typ):
        """Startet Busy sofort und führt Berechnung im nächsten Event-Loop-Tick aus."""
        if not self.get_selected_ids():
            QtWidgets.QMessageBox.warning(
                self,
                "Keine Auswahl",
                "Bitte wählen Sie mindestens ein Element aus."
            )
            return
        busy_text = {
            "bewegungen": "Berechne Bewegungsanalyse ...",
            "bestand": "Berechne Bestandsentwicklung ...",
            "ranking": "Berechne Ranking ...",
            "matrix": "Berechne Matrix-Ansicht ...",
            "verfall": "Berechne Verfallsprognose ...",
        }.get(typ, "Auswertung wird berechnet ...")
        busy_op_id = self._begin_busy(busy_text, delay_ms=0)
        QtCore.QTimer.singleShot(0, lambda t=typ, op=busy_op_id: self._run_auswertung_with_busy(t, op))

    def _run_auswertung_with_busy(self, typ, busy_op_id):
        try:
            self.generate_auswertung(typ)
        finally:
            self._end_busy(busy_op_id)

    def generate_auswertung(self, typ):
        """Generiert die gewählte Auswertung"""
        self.last_auswertung_typ = typ
        selected_ids = self.get_selected_ids()

        if not selected_ids:
            QtWidgets.QMessageBox.warning(
                self,
                "Keine Auswahl",
                "Bitte wählen Sie mindestens ein Element aus."
            )
            return

        self.clear_results()

        start_date = self.date_von.date().toString("yyyy-MM-dd")
        end_date = self.date_bis.date().toString("yyyy-MM-dd")

        if typ == "bewegungen":
            self.show_bewegungen_analyse(selected_ids, start_date, end_date)
        elif typ == "bestand":
            self.show_bestandsentwicklung(selected_ids)
        elif typ == "ranking":
            self.show_ranking(selected_ids, start_date, end_date)
        elif typ == "matrix":
            self.show_matrix_ansicht()
        elif typ == "verfall":
            self.show_verfall_prognose(selected_ids)

    def show_bewegungen_analyse(self, selected_ids, start_date, end_date):
        """Zeigt Bewegungsanalyse mit Aufschlüsselung nach Depot/Präparat"""
        self.results_title.setText("📈 Bewegungsanalyse")

        # Daten holen
        if self.radio_depot.isChecked():
            data = self.db.get_bewegungen_analyse(depot_ids=selected_ids, start_date=start_date, end_date=end_date)
            perspective = "depot"  # Zeige Präparate
        else:
            data = self.db.get_bewegungen_analyse(praeparat_ids=selected_ids, start_date=start_date, end_date=end_date)
            perspective = "praeparat"  # Zeige Depots

        if not data:
            no_data = QtWidgets.QLabel("Keine Bewegungen im gewählten Zeitraum gefunden.")
            no_data.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 14px; padding: 20px;")
            self.content_layout.addWidget(no_data)
            return

        # === KPI BERECHNUNG ===
        total_count = sum(d[4] for d in data)
        zugang_count = sum(d[4] for d in data if d[2] == "Zugang")
        abgang_count = sum(d[4] for d in data if d[2] in ["Abgang", "Vernichtung"])
        
        # Meistbewegtes Element finden
        from collections import Counter
        item_counter = Counter()
        for d in data:
            # d format: (depot, praep, typ, monat, anzahl)
            name = d[1] if self.radio_depot.isChecked() else d[0]
            item_counter[name] += d[4]
        
        most_active_item = item_counter.most_common(1)[0][0] if item_counter else "-"

        self.add_kpi("Gesamt", int(total_count), "EH", AppleTheme.current_colors()['blue'])
        self.add_kpi("Zufluss", int(zugang_count), "EH", AppleTheme.current_colors()['green'])
        self.add_kpi("Abfluss", int(abgang_count), "EH", AppleTheme.current_colors()['red'])
        self.add_kpi("Top Akteur", most_active_item, "", AppleTheme.current_colors()['purple'])

        # === TABELLE MIT DETAILS (HÖHER) ===
        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['Monat', 'Depot', 'Präparat', 'Typ', 'Anzahl'])

        # Daten sortieren und in Tabelle einfügen
        sorted_data = sorted(data, key=lambda x: (x[3] or "0000-00", x[2], x[0], x[1]))
        table.setRowCount(len(sorted_data))

        for row, (depot, praep, typ, monat, anzahl) in enumerate(sorted_data):
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(monat or "Unbekannt"))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(depot))
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(praep))

            typ_item = QtWidgets.QTableWidgetItem(typ)
            if typ == "Zugang":
                typ_item.setForeground(QtGui.QColor("#27ae60"))
            elif typ == "Abgang":
                typ_item.setForeground(QtGui.QColor("#3498db"))
            elif typ == "Vernichtung":
                typ_item.setForeground(QtGui.QColor("#e74c3c"))
            table.setItem(row, 3, typ_item)

            table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(int(anzahl))))

        table.resizeColumnsToContents()
        configure_responsive_table(
            table,
            stretch_columns=[2],
            content_columns=[0, 1, 3, 4],
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setMinimumHeight(260)
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        table_container = ModernChartContainer("Detaillierte Bewegungsliste")
        table_container.add_widget(table)
        self.content_layout.addWidget(table_container)

        # === ACTIONS AKTUALISIEREN ===
        self.update_action_bar("bewegungen", table=table, start_date=start_date, end_date=end_date)

        # === DIAGRAMME NEBENEINANDER ===
        from collections import defaultdict
        from matplotlib.ticker import MaxNLocator
        import numpy as np
        import textwrap
        
        self.bewegungen_canvases = []

        # Container für Diagramme (Flow Layout für Responsiveness)
        charts_widget = QtWidgets.QWidget()
        charts_layout = FlowLayout(charts_widget, margin=0, h_spacing=16, v_spacing=16)
        self.content_layout.addWidget(charts_widget)

        # Setup Matplotlib styling once
        import matplotlib.pyplot as plt
        AppleTheme.setup_matplotlib(plt)
        palette = AppleTheme.get_chart_palette()
        chart_index = 0

        if perspective == "depot":
            praeparate_bewegungen = defaultdict(lambda: defaultdict(lambda: {"Zugang": 0, "Abgang": 0, "Vernichtung": 0}))

            for depot, praep, typ, monat, anzahl in data:
                key = monat if monat else "Unbekannt"
                praeparate_bewegungen[praep][key][typ] += anzahl

            for praep_name, monat_data in praeparate_bewegungen.items():
                fig = Figure(figsize=(4.2, 3.5))  # Höher: 3.5 statt 3.2 für mehrzeilige Titel
                ax = fig.add_subplot(111)

                monate = sorted(monat_data.keys())
                zugaenge = np.array([monat_data[m]["Zugang"] for m in monate])
                abgaenge = np.array([monat_data[m]["Abgang"] for m in monate])
                vernichtungen = np.array([monat_data[m]["Vernichtung"] for m in monate])

                x = np.arange(len(monate))
                width = 0.25

                bars1 = ax.bar(x - width, zugaenge, width, label='Zugang', color=palette[1]) # Greenish
                bars2 = ax.bar(x, abgaenge, width, label='Abgang', color=palette[0]) # Blueish
                bars3 = ax.bar(x + width, vernichtungen, width, label='Vernichtung', color=palette[3]) # Reddish

                # Werte auf Balken schreiben
                def add_value_labels(bars):
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0:
                            ax.text(bar.get_x() + bar.get_width()/2., height,
                                   f'{int(height)}',
                                   ha='center', va='bottom', fontsize=7, fontweight='600')

                add_value_labels(bars1)
                add_value_labels(bars2)
                add_value_labels(bars3)

                ax.set_xlabel('Monat', fontsize=8)
                ax.set_ylabel('Anzahl', fontsize=8)

                # Titel mit Zeilenumbruch (mehr Zeilenabstand für Legende)
                wrapped_title = '\n'.join(textwrap.wrap(praep_name, width=22))
                ax.set_title(wrapped_title, fontsize=10, fontweight='bold', pad=30)

                ax.set_xticks(x)
                ax.set_xticklabels(monate, rotation=30, ha='right', fontsize=9)
                ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=3)
                ax.grid(True, alpha=0.2, axis='y')

                fig.tight_layout(pad=1.5)
                fig.subplots_adjust(bottom=0.3, top=0.75) # Deutlich mehr Platz oben für Titel + Legende
                
                canvas = FigureCanvas(fig)
                canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                canvas.setMinimumSize(360, 300)
                
                chart_card = ModernChartContainer()
                chart_card.add_widget(canvas)
                charts_layout.addWidget(chart_card)

                self.bewegungen_canvases.append((f"Bewegungen: {praep_name}", fig))
                chart_index += 1

        else:
            depot_bewegungen = defaultdict(lambda: defaultdict(lambda: {"Zugang": 0, "Abgang": 0, "Vernichtung": 0}))

            for depot, praep, typ, monat, anzahl in data:
                key = monat if monat else "Unbekannt"
                depot_bewegungen[depot][key][typ] += anzahl

            for depot_name, monat_data in depot_bewegungen.items():
                fig = Figure(figsize=(4.2, 3.5))
                ax = fig.add_subplot(111)

                monate = sorted(monat_data.keys())
                zugaenge = np.array([monat_data[m]["Zugang"] for m in monate])
                abgaenge = np.array([monat_data[m]["Abgang"] for m in monate])
                vernichtungen = np.array([monat_data[m]["Vernichtung"] for m in monate])

                x = np.arange(len(monate))
                width = 0.25

                bars1 = ax.bar(x - width, zugaenge, width, label='Zugang', color=palette[1])
                bars2 = ax.bar(x, abgaenge, width, label='Abgang', color=palette[0])
                bars3 = ax.bar(x + width, vernichtungen, width, label='Vernichtung', color=palette[3])

                # Werte auf Balken schreiben
                def add_value_labels(bars):
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0:
                            ax.text(bar.get_x() + bar.get_width()/2., height,
                                   f'{int(height)}',
                                   ha='center', va='bottom', fontsize=7, fontweight='600')

                add_value_labels(bars1)
                add_value_labels(bars2)
                add_value_labels(bars3)

                ax.set_xlabel('Monat', fontsize=8)
                ax.set_ylabel('Anzahl', fontsize=8)

                # Titel mit Zeilenumbruch (mehr Zeilenabstand für Legende)
                wrapped_title = '\n'.join(textwrap.wrap(depot_name, width=22))
                ax.set_title(wrapped_title, fontsize=10, fontweight='bold', pad=30)

                ax.set_xticks(x)
                ax.set_xticklabels(monate, rotation=30, ha='right', fontsize=9)
                ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=3)
                ax.grid(True, alpha=0.2, axis='y')

                fig.tight_layout(pad=1.5)
                fig.subplots_adjust(bottom=0.3, top=0.75)
                
                canvas = FigureCanvas(fig)
                canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                canvas.setMinimumSize(360, 300)
                
                chart_card = ModernChartContainer()
                chart_card.add_widget(canvas)
                charts_layout.addWidget(chart_card)

                self.bewegungen_canvases.append((f"Bewegungen: {depot_name}", fig))
                chart_index += 1

        # Speichere Tabellen-Daten für PDF

        # Speichere Tabellen-Daten für PDF (inkl. KPIs für den Export)
        self.bewegungen_table_data = {
            'table': table,
            'sorted_data': sorted_data,
            'headers': ['Monat', 'Depot', 'Präparat', 'Typ', 'Anzahl'],
            'kpis': [
                ("Gesamtbewegungen", f"{int(total_count)} EH"),
                ("Gesamt Zufluss", f"{int(zugang_count)} EH"),
                ("Gesamt Abfluss", f"{int(abgang_count)} EH"),
                ("Top Akteur", most_active_item)
            ]
        }

        # (Actions werden jetzt zentral in update_action_bar verwaltet)
        
        self.content_layout.addStretch()

    def export_bewegungen_tabelle_pdf(self, table, start_date, end_date):
        """Exportiert nur die Bewegungen-Tabelle als PDF"""
        file_path = self._save_file_path(
            "PDF speichern",
            f"Bewegungen_Tabelle_{start_date}_{end_date}.pdf",
            "PDF Files (*.pdf)",
        )

        if not file_path:
            return

        op_id = self._begin_busy(self._export_report_message or "Erstelle PDF …", delay_ms=0)
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from datetime import datetime

            # PDF erstellen
            doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
            elements = []

            # Titel
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1c1c1e'),
                spaceAfter=20,
                alignment=1
            )
            elements.append(Paragraph(f"Bewegungsanalyse ({start_date} bis {end_date})", title_style))
            
            # KPI Sektion im PDF
            if hasattr(self, 'bewegungen_table_data') and 'kpis' in self.bewegungen_table_data:
                kpi_data = []
                # KPIs in 2er Reihen
                kpis = self.bewegungen_table_data['kpis']
                for i in range(0, len(kpis), 2):
                    row = []
                    for j in range(2):
                        if i+j < len(kpis):
                            label, val = kpis[i+j]
                            row.append(Paragraph(f"<b>{label}:</b> {val}", styles['Normal']))
                    kpi_data.append(row)
                
                kpi_table = Table(kpi_data, colWidths=[2.5*inch, 2.5*inch])
                kpi_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f2f2f7')),
                    ('ROUNDEDCORNERS', [8, 8, 8, 8]),
                    ('TOPPADDING', (0,0), (-1,-1), 10),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                    ('LEFTPADDING', (0,0), (-1,-1), 15),
                    ('GRID', (0,0), (-1,-1), 0, colors.white),
                ]))
                elements.append(kpi_table)
                elements.append(Spacer(1, 0.3*inch))

            # Tabellendaten
            table_data = [['Monat', 'Depot', 'Präparat', 'Typ', 'Anzahl']]
            for row in range(table.rowCount()):
                row_data = []
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    row_data.append(item.text() if item else "")
                table_data.append(row_data)

            # Tabelle mit modernem Apple-Styling
            pdf_table = Table(table_data, colWidths=[1.1*inch, 1.4*inch, 1.7*inch, 1.1*inch, 0.8*inch])
            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007aff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e5ea')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fbfbfd')])
            ]))

            elements.append(pdf_table)

            # Erstellungsdatum
            elements.append(Spacer(1, 0.4*inch))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=2
            )
            elements.append(Paragraph(f"Erstellt mit ND-Hub Analytics V36 | {datetime.now().strftime('%d.%m.%Y %H:%M')}", footer_style))

            doc.build(elements)

            QtWidgets.QMessageBox.information(self, "✅ Erfolg", f"Tabelle exportiert:\n{file_path}")

        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Fehler", "reportlab ist nicht installiert.\nInstalliere mit: pip install reportlab")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "❌ Fehler", f"Fehler beim Exportieren:\n{str(e)}")
        finally:
            self._end_busy(op_id)

    def export_bewegungen_all_pdf(self, start_date, end_date):
        """Exportiert alle Diagramme der Bewegungsanalyse als PDF"""
        file_path = self._save_file_path(
            "PDF speichern",
            f"Bewegungen_Analyse_{start_date}_{end_date}.pdf",
            "PDF Files (*.pdf)",
        )

        if not file_path:
            return

        op_id = self._begin_busy(self._export_charts_message or "Exportiere Diagramme …", delay_ms=0)
        try:
            from matplotlib.backends.backend_pdf import PdfPages
            from datetime import datetime

            if not hasattr(self, 'bewegungen_canvases') or not self.bewegungen_canvases:
                QtWidgets.QMessageBox.warning(self, "Warnung", "Keine Diagramme zum Exportieren vorhanden.")
                return

            with PdfPages(file_path) as pdf:
                for title, fig in self.bewegungen_canvases:
                    pdf.savefig(fig, bbox_inches='tight')

                # Metadaten
                d = pdf.infodict()
                d['Title'] = 'Bewegungsanalyse'
                d['Author'] = 'ND-Hub Manager'
                d['Subject'] = f'Bewegungsanalyse {start_date} bis {end_date}'
                d['Keywords'] = 'Bewegungen, Depots, Präparate'
                d['CreationDate'] = datetime.now()

            QtWidgets.QMessageBox.information(self, "✅ Erfolg", f"Diagramme exportiert:\n{file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "❌ Fehler", f"Fehler beim Exportieren:\n{str(e)}")
        finally:
            self._end_busy(op_id)

    def show_bestandsentwicklung(self, selected_ids):
        """Zeigt Bestandsentwicklung mit Soll/Ist-Vergleich"""
        self.results_title.setText("Bestandsentwicklung (Soll vs. Ist)")

        # Daten holen
        if self.radio_depot.isChecked():
            data = self.db.get_bestandsentwicklung(depot_ids=selected_ids)
        else:
            data = self.db.get_bestandsentwicklung(praeparat_ids=selected_ids)

        if not data:
            no_data = QtWidgets.QLabel("Keine Bestandsdaten gefunden.")
            no_data.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 14px; padding: 20px;")
            self.content_layout.addWidget(no_data)
            return

        # === KPI BERECHNUNG ===
        sum_soll = sum(d[2] for d in data)
        sum_ist = sum(d[3] for d in data)
        quote = (sum_ist / sum_soll * 100) if sum_soll > 0 else 0
        luecken = sum(1 for d in data if d[3] < d[2])
        
        self.add_kpi("Bestandsquote", f"{quote:.1f}", "%", AppleTheme.current_colors()['blue'])
        self.add_kpi("Kritische Lücken", luecken, "Items", AppleTheme.current_colors()['red'] if luecken > 0 else AppleTheme.current_colors()['green'])
        self.add_kpi("Gesamtbestand", int(sum_ist), "EH", AppleTheme.current_colors()['orange'])

        # Tabelle erstellen
        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['Depot', 'Präparat', 'Soll', 'Ist', 'Differenz'])
        table.setRowCount(len(data))

        for row, (depot, praep, soll, ist, diff) in enumerate(data):
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(depot))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(praep))
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(soll)))
            table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(ist)))

            diff_item = QtWidgets.QTableWidgetItem(str(diff))
            # Farbcodierung
            if diff < 0:
                diff_item.setBackground(QtGui.QColor("#ffebee"))  # Rot (Unterbestand)
                diff_item.setForeground(QtGui.QColor("#c62828"))
            elif diff > 0:
                diff_item.setBackground(QtGui.QColor("#e8f5e9"))  # Grün (Überbestand)
                diff_item.setForeground(QtGui.QColor("#2e7d32"))

            table.setItem(row, 4, diff_item)

        table.resizeColumnsToContents()
        configure_responsive_table(
            table,
            stretch_columns=[1],
            content_columns=[0, 2, 3, 4],
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setMinimumHeight(220)
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.content_layout.addWidget(table)

        # Diagramm: Soll vs. Ist
        import matplotlib.pyplot as plt
        AppleTheme.setup_matplotlib(plt)
        palette = AppleTheme.get_chart_palette()

        fig = Figure(figsize=(10, 4.5))
        ax = fig.add_subplot(111)

        labels = [textwrap.fill(f"{depot} - {praep}", 15) for depot, praep, *_ in data]
        soll_werte = [soll for _, _, soll, _, _ in data]
        ist_werte = [ist for _, _, _, ist, _ in data]

        x = np.arange(len(labels))
        width = 0.35

        ax.bar(x - width/2, soll_werte, width, label='Sollbestand', color=palette[0], alpha=0.6)
        ax.bar(x + width/2, ist_werte, width, label='Ist-Bestand', color=palette[1])

        ax.set_ylabel('Anzahl', fontsize=10)
        ax.set_title('Direkter Bestandsabgleich', fontsize=12, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=35, ha='right', fontsize=8)
        ax.legend(fontsize=9, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=2, frameon=False)
        ax.grid(True, alpha=0.2, axis='y')

        fig.tight_layout(pad=1.5)
        fig.subplots_adjust(bottom=0.35, top=0.78)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(400)
        
        chart_container = ModernChartContainer()
        chart_container.add_widget(canvas)
        self.content_layout.addWidget(chart_container)

        # === ACTIONS AKTUALISIEREN ===
        self.update_action_bar("bestand", table=table, canvases=[("Bestandsvergleich", fig)])

        self.content_layout.addStretch()

    def show_ranking(self, selected_ids, start_date, end_date):
        """Zeigt Top-Rankings"""
        if self.radio_depot.isChecked():
            self.results_title.setText("🏆 Top Präparate (nach Abgaben)")
            data = self.db.get_praeparat_ranking(depot_ids=selected_ids, start_date=start_date, end_date=end_date, limit=10)
            label_field = 0  # praeparat_name
            x_label = "Präparat"
        else:
            self.results_title.setText("🏆 Top Depots (nach Abgaben)")
            data = self.db.get_depot_ranking(praeparat_ids=selected_ids, start_date=start_date, end_date=end_date, limit=10)
            label_field = 0  # depot_name
            x_label = "Depot"

        if not data:
            no_data = QtWidgets.QLabel("Keine Abgaben im gewählten Zeitraum gefunden.")
            no_data.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 14px; padding: 20px;")
            self.content_layout.addWidget(no_data)
            return

        # === KPI BERECHNUNG ===
        top_name = data[0][label_field]
        top_value = data[0][2]
        total_volume = sum(d[2] for d in data)
        
        self.add_kpi("Spitzenreiter", top_name, "", AppleTheme.current_colors()['purple'])
        self.add_kpi("Max. Volumen", int(top_value), "EH", AppleTheme.current_colors()['blue'])
        self.add_kpi("Gesamtvolumen", int(total_volume), "EH", AppleTheme.current_colors()['green'])

        # Tabelle
        table = QtWidgets.QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([x_label, 'Verbrauch', '% Anteil'])
        table.setRowCount(len(data))

        for row, d in enumerate(data):
            val = d[2]
            perc = (val / total_volume * 100) if total_volume > 0 else 0
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(d[label_field]))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(int(val))))
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{perc:.1f}%"))

        table.resizeColumnsToContents()
        configure_responsive_table(
            table,
            stretch_columns=[0],
            content_columns=[1, 2],
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(220)
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        table_card = ModernChartContainer("Ranking Tabelle")
        table_card.add_widget(table)
        self.content_layout.addWidget(table_card)

        # Diagramm: Horizontales Ranking
        import matplotlib.pyplot as plt
        AppleTheme.setup_matplotlib(plt)
        palette = AppleTheme.get_chart_palette()

        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(111)

        names = [d[label_field] for d in data][::-1] # Umkehren für Top-Down
        values = [d[2] for d in data][::-1]

        bars = ax.barh(names, values, color=palette[4]) # Purple logic

        # Werte an die Balken schreiben
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)}', ha='left', va='center', fontsize=9, fontweight='bold')

        plural_suffix = "e" if x_label == "Präparat" else "s"
        ax.set_title(f"Top 10 {x_label}{plural_suffix}", fontsize=12, fontweight='bold', pad=15)
        ax.set_xlabel("Verbrauchte Einheiten")
        ax.grid(True, alpha=0.1, axis='x')

        fig.tight_layout()
        
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(350)
        
        chart_card = ModernChartContainer()
        chart_card.add_widget(canvas)
        self.content_layout.addWidget(chart_card)

        # === ACTIONS AKTUALISIEREN ===
        self.update_action_bar("ranking", table=table, canvases=[(f"Ranking {x_label}e", fig)])

        self.content_layout.addStretch()
        self.content_layout.addStretch()

    def show_matrix_ansicht(self):
        """Zeigt Matrix/Heatmap (Depot × Präparat)"""
        self.results_title.setText("🗺️ Matrix-Ansicht: Abweichungen vom Sollbestand")

        data = self.db.get_matrix_data()

        if not data:
            no_data = QtWidgets.QLabel("Keine Matrix-Daten verfügbar.")
            no_data.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 14px; padding: 20px;")
            self.content_layout.addWidget(no_data)
            return

        # === KPI BERECHNUNG ===
        kritisch = sum(1 for row in data if (row[3] or 0) < (row[2] or 0))
        ueberschuss = sum(1 for row in data if (row[3] or 0) > (row[2] or 0))
        gesamt_zellen = len(data)
        
        self.add_kpi("Fehlbestand", kritisch, "Zellen", AppleTheme.current_colors()['red'] if kritisch > 0 else AppleTheme.current_colors()['green'])
        self.add_kpi("Überschuss", ueberschuss, "Zellen", AppleTheme.current_colors()['blue'])
        self.add_kpi("Gesamtmatrix", gesamt_zellen, "Kombis", AppleTheme.current_colors()['secondary_label'])

        # Daten vorbereiten für Heatmap
        import numpy as np

        # Eindeutige Depots und Präparate sammeln
        depots = sorted(set(row[0] for row in data))
        praeparate = sorted(set(row[1] for row in data))

        # Matrix erstellen
        matrix = np.zeros((len(depots), len(praeparate)))

        for depot_name, praep_name, soll, ist in data:
            depot_idx = depots.index(depot_name)
            praep_idx = praeparate.index(praep_name)
            
            # Sichere Defaults
            soll = soll or 0
            ist = ist or 0
            
            # Abweichung in Prozent (oder absolut wenn Soll=0)
            if soll > 0:
                abweichung = ((ist - soll) / soll) * 100
            else:
                abweichung = ist
            
            matrix[depot_idx, praep_idx] = abweichung


        # Heatmap erstellen
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        AppleTheme.setup_matplotlib(plt)

        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(111)

        # Custom Colormap: Rot -> Weiß -> Grün
        # Wir nutzen eine divergierende Map: Rot für Fehlbestand, Weiß für Punktlandung, Grün für Überschuss
        cmap = mcolors.LinearSegmentedColormap.from_list("apple_matrix", ["#ff3b30", "#ffffff", "#34c759"])
        
        # Normierung so, dass 0 immer in der Mitte (Weiß) ist
        vmin = matrix.min() if matrix.min() < 0 else -1
        vmax = matrix.max() if matrix.max() > 0 else 1
        norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

        im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect='auto')

        # Beschriftungen
        ax.set_xticks(np.arange(len(praeparate)))
        ax.set_yticks(np.arange(len(depots)))
        ax.set_xticklabels(praeparate, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(depots, fontsize=8)

        # Werte nur anzeigen, wenn Matrix nicht zu riesig ist
        if len(depots) < 20 and len(praeparate) < 15:
            for i in range(len(depots)):
                for j in range(len(praeparate)):
                    val = int(matrix[i, j])
                    if val != 0:
                        ax.text(j, i, f"{val:+d}", ha="center", va="center", 
                               color="black" if abs(val) < 5 else "white", 
                               fontsize=7, fontweight='bold')

        ax.set_title("Bestands-Abweichungs-Matrix (Differenz)", fontsize=12, fontweight='bold', pad=20)
        
        fig.tight_layout()

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(450)
        
        chart_card = ModernChartContainer()
        chart_card.add_widget(canvas)
        self.content_layout.addWidget(chart_card)

        # === ACTIONS AKTUALISIEREN ===
        self.update_action_bar("matrix", canvases=[("Bestandsmatrix", fig)])

        # Legende / Colorbar integrieren
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=8)
        cbar.set_label('Abweichung (Ist - Soll)', fontsize=9)

    def show_verfall_prognose(self, selected_ids):
        """Zeigt eine Vorhersage, wann wie viele Präparate verfallen."""
        self.results_title.setText("⏳ Verfalls-Prognose (Nächste 24 Monate)")

        # Wir können direkt SQLite nutzen, um die Verfalldaten zu gruppieren
        placeholders = ','.join('?' * len(selected_ids))
        
        if self.radio_depot.isChecked():
            where_clause = f"b.depot_id IN ({placeholders})"
        else:
            where_clause = f"b.praeparat_id IN ({placeholders})"

        # Zähle alle noch nicht abgegangenen Chargen, gruppiert nach Verfallsmonat
        sql = f"""
            SELECT 
                strftime('%Y-%m', b.verfall) as verfall_monat,
                SUM(b.anzahl) as anzahl
            FROM bewegungen b
            WHERE {where_clause}
              AND b.typ = 'Zugang'
              AND (b.ausgang_datum IS NULL OR b.ausgang_datum = '')
              AND b.verfall IS NOT NULL
              AND b.verfall != ''
            GROUP BY verfall_monat
            ORDER BY verfall_monat
        """
        
        data = self.db.cur.execute(sql, selected_ids).fetchall()

        if not data:
            no_data = QtWidgets.QLabel("Keine Verfallsdaten gefunden.")
            no_data.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 14px; padding: 20px;")
            self.content_layout.addWidget(no_data)
            return

        import datetime
        from dateutil.relativedelta import relativedelta
        import matplotlib.pyplot as plt
        import numpy as np

        # Filtere auf die nächsten 24 Monate inkl. historisch (bereits verfallen)
        today = datetime.date.today()
        current_month = f"{today.year}-{today.month:02d}"
        future_cutoff = (today + relativedelta(months=24)).strftime("%Y-%m")

        filtered_data = [d for d in data if d[0] and d[0] <= future_cutoff]
        
        if not filtered_data:
            no_data = QtWidgets.QLabel("Keine Verfalldaten bis zum gewählten Horizont gefunden.")
            no_data.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 14px; padding: 20px;")
            self.content_layout.addWidget(no_data)
            return

        # KPIs berechnen
        bereits_verfallen = sum(d[1] for d in filtered_data if d[0] < current_month)
        verfallen_naechste_3_monate = sum(d[1] for d in filtered_data if current_month <= d[0] <= (today + relativedelta(months=3)).strftime("%Y-%m"))
        gesamt_gefaehrdet = sum(d[1] for d in filtered_data)

        self.add_kpi("Bereits verfallen", int(bereits_verfallen), "EH", AppleTheme.current_colors()['red'])
        self.add_kpi("Kritisch (<3 Mon.)", int(verfallen_naechste_3_monate), "EH", AppleTheme.current_colors()['orange'])
        self.add_kpi("Vorschau Gesamt", int(gesamt_gefaehrdet), "EH", AppleTheme.current_colors()['blue'])

        # Chart: Ein Balkendiagramm der Verfallsmengen pro Monat
        AppleTheme.setup_matplotlib(plt)
        palette = AppleTheme.get_chart_palette()

        fig = Figure(figsize=(10, 4.5))
        ax = fig.add_subplot(111)

        monate = [d[0] for d in filtered_data]
        mengen = [d[1] for d in filtered_data]

        x = np.arange(len(monate))
        
        # Color coding: Red for past, Orange for < 3 months, Green for rest
        bar_colors = []
        for m in monate:
            if m < current_month:
                bar_colors.append(palette[3]) # red
            elif m <= (today + relativedelta(months=3)).strftime("%Y-%m"):
                bar_colors.append(palette[2]) # orange
            else:
                bar_colors.append(palette[1]) # green

        bars = ax.bar(x, mengen, color=bar_colors)

        # Aktueller Monat als Linie
        try:
            if current_month in monate:
                curr_idx = monate.index(current_month)
                ax.axvline(x=curr_idx - 0.5, color=palette[0], linestyle='--', alpha=0.5)
                ax.text(curr_idx - 0.5, ax.get_ylim()[1]*0.9, ' Heute', color=palette[0], fontsize=8, fontweight='bold')
        except ValueError:
            pass

        # Werte über den Balken
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + (max(mengen)*0.02),
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=8, fontweight='bold')

        ax.set_title('Verfalls-Prognose pro Monat', fontsize=12, fontweight='bold', pad=15)
        ax.set_ylabel('Anzahl der Einheiten', fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(monate, rotation=35, ha='right', fontsize=9)
        ax.grid(True, alpha=0.1, axis='y')

        fig.tight_layout(pad=1.5)
        fig.subplots_adjust(bottom=0.35)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(400)
        
        chart_card = ModernChartContainer("Verlauf drohender Verfallsdaten")
        chart_card.add_widget(canvas)
        self.content_layout.addWidget(chart_card)

        # === ACTIONS AKTUALISIEREN ===
        self.update_action_bar("verfall", canvases=[("Verfallsprognose", fig)])

        self.content_layout.addStretch()

    def export_generic_table_pdf(self, title, table):
        """Exportiert eine beliebige Tabelle als PDF"""
        file_path = self._save_file_path(
            "Bericht speichern",
            f"NDHub_{title}_{datetime.now().strftime('%Y%m%d')}.pdf",
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return

        op_id = self._begin_busy(self._export_report_message or "Erstelle Bericht …", delay_ms=0)
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors

            doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=0.5*inch)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph(f"{title} - Bericht", ParagraphStyle('T', parent=styles['Heading1'], fontSize=18, spaceAfter=20)))
            
            # Daten extrahieren
            data = []
            headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
            data.append(headers)
            
            for row in range(table.rowCount()):
                row_data = [table.item(row, col).text() if table.item(row, col) else "" for col in range(table.columnCount())]
                data.append(row_data)

            pdf_table = Table(data, hAlign='LEFT')
            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#007aff')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 9),
            ]))
            elements.append(pdf_table)
            doc.build(elements)
            QtWidgets.QMessageBox.information(self, "Erfolg", "Bericht wurde gespeichert.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Export: {e}")
        finally:
            self._end_busy(op_id)

    def export_generic_charts_pdf(self, title, canvases):
        """Exportiert mehrere Grafiken in ein PDF"""
        if not canvases:
            return
        file_path = self._save_file_path(
            "Grafiken speichern",
            f"NDHub_Grafiken_{title}_{datetime.now().strftime('%Y%m%d')}.pdf",
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return

        op_id = self._begin_busy(self._export_charts_message or "Exportiere Grafiken …", delay_ms=0)
        try:
            from matplotlib.backends.backend_pdf import PdfPages
            with PdfPages(file_path) as pdf:
                for label, fig in canvases:
                    pdf.savefig(fig, bbox_inches='tight')
            QtWidgets.QMessageBox.information(self, "Erfolg", "Grafiken wurden gespeichert.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler beim Export: {e}")
        finally:
            self._end_busy(op_id)
