import os
from PySide6 import QtWidgets, QtCore, QtGui
from icon_manager import IconManager
from apple_theme import AppleTheme

class PPTExportDialog(QtWidgets.QDialog):
    def __init__(self, db_manager, default_depot_ids=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.default_depots = default_depot_ids or []
        
        self.setWindowTitle("PowerPoint Management Report erstellen")
        self.setMinimumWidth(500)
        self.setStyleSheet(AppleTheme.get_stylesheet())
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QtWidgets.QLabel("Management Präsentation")
        header.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(header)
        
        info = QtWidgets.QLabel("Generieren Sie eine professionelle PowerPoint-Datei (.pptx) mit aktuellen KPIs und Analysen für das Management.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']};")
        layout.addWidget(info)
        
        # Form
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(15)
        
        self.input_title = QtWidgets.QLineEdit("Jahresbilanz Notfalldepots")
        self.input_subtitle = QtWidgets.QLineEdit("Management Summary & Analyse")
        
        form_layout.addRow("Titel:", self.input_title)
        form_layout.addRow("Untertitel:", self.input_subtitle)
        
        # Selection
        self.depot_checkboxes = []
        depot_group = QtWidgets.QGroupBox("Zu analysierende Depots")
        depot_layout = QtWidgets.QVBoxLayout(depot_group)
        
        depots = self.db.list_depots()
        
        self.cb_all_depots = QtWidgets.QCheckBox("Alle Depots einschließen")
        if not self.default_depots:
            self.cb_all_depots.setChecked(True)
        self.cb_all_depots.toggled.connect(self._toggle_depots)
        depot_layout.addWidget(self.cb_all_depots)
        
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        
        for d_id, d_name, *_ in depots:
            cb = QtWidgets.QCheckBox(d_name)
            cb.setProperty("depot_id", d_id)
            if self.default_depots and d_id in self.default_depots:
                cb.setChecked(True)
            elif not self.default_depots:
                cb.setChecked(True)
                cb.setEnabled(False)
            self.depot_checkboxes.append(cb)
            scroll_layout.addWidget(cb)
            
        scroll.setWidget(scroll_widget)
        depot_layout.addWidget(scroll)
        layout.addWidget(depot_group)
        
        # Features Group
        feat_group = QtWidgets.QGroupBox("Features & Inhalte")
        feat_layout = QtWidgets.QVBoxLayout(feat_group)
        
        self.cb_kpi = QtWidgets.QCheckBox("Management Summary (Erweiterte KPIs)")
        self.cb_kpi.setChecked(True)
        
        self.cb_bestand = QtWidgets.QCheckBox("Soll-Ist Bestandsvergleich (Natives Diagramm)")
        self.cb_bestand.setChecked(True)
        
        self.cb_ranking = QtWidgets.QCheckBox("Top Präparate Ranking (Balkendiagramm)")
        self.cb_ranking.setChecked(True)
        
        self.cb_insights = QtWidgets.QCheckBox("Automatisierte Handlungsempfehlungen (Text-Slide)")
        self.cb_insights.setChecked(True)
        
        feat_layout.addWidget(self.cb_kpi)
        feat_layout.addWidget(self.cb_bestand)
        feat_layout.addWidget(self.cb_ranking)
        feat_layout.addWidget(self.cb_insights)
        layout.addWidget(feat_group)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QtWidgets.QPushButton("Abbrechen")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.clicked.connect(self.reject)
        
        btn_export = QtWidgets.QPushButton(" Präsentation Generieren")
        btn_export.setIcon(IconManager.get_icon("monitor"))
        btn_export.setObjectName("btn_add")
        btn_export.clicked.connect(self.generate_ppt)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_export)
        
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        
    def _toggle_depots(self, checked):
        for cb in self.depot_checkboxes:
            cb.setEnabled(not checked)
            if checked:
                cb.setChecked(True)
                
    def get_selected_depots(self):
        if self.cb_all_depots.isChecked():
            return [] # Empty means all
        return [cb.property("depot_id") for cb in self.depot_checkboxes if cb.isChecked()]

    def generate_ppt(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window(),
            "PowerPoint speichern",
            f"Management_Report_{QtCore.QDate.currentDate().toString('yyyyMMdd')}.pptx",
            "PowerPoint Files (*.pptx)",
            "",
            QtWidgets.QFileDialog.Option.DontUseNativeDialog,
        )
        
        if not file_path: return
        
        config = {
            'title': self.input_title.text(),
            'subtitle': self.input_subtitle.text(),
            'depots': self.get_selected_depots(),
            'kpi': self.cb_kpi.isChecked(),
            'bestand': self.cb_bestand.isChecked(),
            'ranking': self.cb_ranking.isChecked(),
            'insights': self.cb_insights.isChecked()
        }
        
        try:
            from tools.ppt_exporter import PPTGenerator
            generator = PPTGenerator(self.db)
            generator.generate(file_path, config)
            QtWidgets.QMessageBox.information(self, "Erfolg", "Präsentation wurde erfolgreich generiert!")
            self.accept()
            # Open automatically
            if hasattr(os, "startfile"):
                os.startfile(file_path)  # nosec B606: opens user-selected output file with OS default app
        except ModuleNotFoundError as e:
            if "pptx" in str(e):
                QtWidgets.QMessageBox.warning(
                    self,
                    "PowerPoint-Modul fehlt",
                    "Für den PowerPoint-Export fehlt das Paket 'python-pptx'.\n\n"
                    "Lösung:\n"
                    "1. Schließen Sie die Anwendung.\n"
                    "2. Führen Sie './setup_env.sh' im Terminal aus.\n"
                    "3. Starten Sie die Anwendung neu.\n\n"
                    "Alternativ (manuell):\n"
                    "pip install python-pptx"
                )
                return
            raise
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Fehler bei der PPT-Erstellung:\n{str(e)}")
