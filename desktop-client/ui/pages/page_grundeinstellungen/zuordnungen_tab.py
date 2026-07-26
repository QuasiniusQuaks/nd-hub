"""Zuordnungen - Depot ↔ Präparate zuordnen mit Sollbestand."""
from apple_theme import AppleTheme
from db_manager import Database
from icon_manager import IconManager
from PySide6 import QtWidgets

from ui.utils import create_card_widget


class AssignmentPage(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QtWidgets.QLabel("Depot ↔ Präparate zuordnen")
        title.setProperty("class", "page-title")
        layout.addWidget(title)

        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(12)
        lbl_depot = QtWidgets.QLabel("Depot auswählen:")
        lbl_depot.setStyleSheet("font-weight: 600;")
        self.cb_depot = QtWidgets.QComboBox()
        self.cb_depot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        top.addWidget(lbl_depot)
        top.addWidget(self.cb_depot, 1)
        top.addStretch()
        card_layout.addLayout(top)

        self.info_label = QtWidgets.QLabel(
            "Wählen Sie die Präparate aus und legen Sie den Sollbestand pro Depot fest:"
        )
        self.info_label.setWordWrap(True)
        self._apply_assignment_info_style()
        card_layout.addWidget(self.info_label)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.box = QtWidgets.QWidget()
        self.scroll.setWidget(self.box)
        self.vbox_checks = QtWidgets.QVBoxLayout(self.box)
        self.vbox_checks.setSpacing(12)
        card_layout.addWidget(self.scroll)

        self.btn_save = QtWidgets.QPushButton(" Zuordnung speichern")
        self.btn_save.setIcon(IconManager.get_icon("check"))
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setMinimumHeight(40)
        card_layout.addWidget(self.btn_save)

        layout.addWidget(card)

        self.cb_depot.currentIndexChanged.connect(self.populate_checks)
        self.btn_save.clicked.connect(self.save_assignment)

        self.refresh_depots()
        self.populate_checks()

    def _apply_assignment_info_style(self) -> None:
        c = AppleTheme.current_colors()
        self.info_label.setStyleSheet(
            f"color: {c['secondary_label']}; font-size: 12px; padding: 8px 0;"
        )

    def refresh_theme(self) -> None:
        self._apply_assignment_info_style()

    def refresh_depots(self):
        self.cb_depot.clear()
        self.depots = self.db.list_depots()
        for d in self.depots:
            self.cb_depot.addItem(d[1], d[0])

    def populate_checks(self):
        while self.vbox_checks.count():
            item = self.vbox_checks.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if self.cb_depot.count() == 0:
            self.vbox_checks.addWidget(QtWidgets.QLabel("Keine Depots vorhanden."))
            return

        depot_id = self.cb_depot.currentData()
        assignments = self.db.get_depot_praeparat_assignments(depot_id)

        self.check_items = []
        prae_list = self.db.list_praeparate()

        if not prae_list:
            self.vbox_checks.addWidget(QtWidgets.QLabel("Keine Präparate vorhanden."))
            return

        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 8)

        c = AppleTheme.current_colors()
        lbl_praeaparat = QtWidgets.QLabel("Präparat")
        lbl_praeaparat.setStyleSheet(f"font-weight: 600; color: {c['label']};")
        lbl_sollbestand = QtWidgets.QLabel("Sollbestand (Packungen)")
        lbl_sollbestand.setStyleSheet(f"font-weight: 600; color: {c['label']};")

        header_layout.addWidget(lbl_praeaparat, 1)
        header_layout.addWidget(lbl_sollbestand)

        self.vbox_checks.addWidget(header_widget)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet(f"background-color: {c['separator']};")
        self.vbox_checks.addWidget(line)

        for pid, pname in prae_list:
            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 4, 0, 4)
            row_layout.setSpacing(12)

            cb = QtWidgets.QCheckBox(pname)
            is_assigned = pid in assignments
            cb.setChecked(is_assigned)

            spin = QtWidgets.QSpinBox()
            spin.setRange(0, 99999)
            spin.setValue(assignments.get(pid, 0))
            spin.setEnabled(is_assigned)
            spin.setMinimumWidth(120)
            spin.setSuffix(" Pkg.")

            cb.toggled.connect(lambda checked, s=spin: s.setEnabled(checked))

            row_layout.addWidget(cb, 1)
            row_layout.addWidget(spin)

            self.vbox_checks.addWidget(row_widget)
            self.check_items.append((cb, spin, pid))

        self.vbox_checks.addStretch()

    def save_assignment(self):
        if self.cb_depot.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Hinweis", "Bitte zuerst ein Depot anlegen.")
            return

        depot_id = self.cb_depot.currentData()
        praeparat_sollbestand = {}

        for cb, spin, pid in self.check_items:
            if cb.isChecked():
                sollbestand = spin.value()
                praeparat_sollbestand[pid] = sollbestand

        self.db.set_assigned_praeparate_with_sollbestand(depot_id, praeparat_sollbestand)
        QtWidgets.QMessageBox.information(self, "Gespeichert",
                                         f"Zuordnungen mit Sollbeständen für {len(praeparat_sollbestand)} Präparate gespeichert.")
