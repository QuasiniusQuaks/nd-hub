"""Bewegungen erfassen - Einzelpage für das QStackedWidget."""
import os

from db_manager import Database, to_iso
from icon_manager import IconManager
from PySide6 import QtWidgets
from PySide6.QtCore import QDate, Qt

from ui.utils import create_card_widget


class BewegungenPage(QtWidgets.QWidget):
    def __init__(self, db: Database, attachment_base_folder: str, security=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.security = security
        self.attachment_base_folder = attachment_base_folder
        self.attachment_file = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QtWidgets.QLabel("Bewegungen erfassen")
        title.setProperty("class", "page-title")
        layout.addWidget(title)

        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)

        form = QtWidgets.QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignRight)
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)

        self.cb_typ = QtWidgets.QComboBox()
        self.cb_typ.addItems(["Zugang", "Abgang", "Vernichtung"])
        form.addRow("Typ:", self.cb_typ)

        self.cb_depot = QtWidgets.QComboBox()
        self.cb_depot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form.addRow("Depot:", self.cb_depot)

        self.cb_praeparat = QtWidgets.QComboBox()
        self.cb_praeparat.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form.addRow("Präparat:", self.cb_praeparat)

        self.e_charge = QtWidgets.QLineEdit()
        form.addRow("Charge:", self.e_charge)

        self.d_verfall = QtWidgets.QDateEdit(calendarPopup=True)
        self.d_verfall.setDisplayFormat("yyyy-MM-dd")
        self.d_verfall.setDate(QDate.currentDate())
        form.addRow("Verfall:", self.d_verfall)

        self.d_eingang = QtWidgets.QDateEdit(calendarPopup=True)
        self.d_eingang.setDisplayFormat("yyyy-MM-dd")
        self.d_eingang.setDate(QDate.currentDate())
        form.addRow("Eingangsdatum:", self.d_eingang)

        self.d_ausgang = QtWidgets.QDateEdit(calendarPopup=True)
        self.d_ausgang.setDisplayFormat("yyyy-MM-dd")
        self.d_ausgang.setDate(QDate.currentDate())
        form.addRow("Ausgangsdatum:", self.d_ausgang)

        self.e_empfaenger = QtWidgets.QLineEdit()
        form.addRow("Empfänger:", self.e_empfaenger)

        self.spin_anzahl = QtWidgets.QSpinBox()
        self.spin_anzahl.setRange(1, 1000000)
        self.spin_anzahl.setValue(1)
        form.addRow("Anzahl:", self.spin_anzahl)

        attach_widget = QtWidgets.QWidget()
        attach_layout = QtWidgets.QHBoxLayout(attach_widget)
        attach_layout.setContentsMargins(0, 0, 0, 0)
        attach_layout.setSpacing(12)

        self.lbl_attachment = QtWidgets.QLabel("Keine Datei ausgewählt")
        self.lbl_attachment.setObjectName("attachment_label")
        self.lbl_attachment.setWordWrap(True)
        self.btn_select_file = QtWidgets.QPushButton(" Datei auswählen")
        self.btn_select_file.setIcon(IconManager.get_icon("paperclip"))
        self.btn_select_file.setMinimumWidth(120)
        self.btn_clear_file = QtWidgets.QPushButton("")
        self.btn_clear_file.setIcon(IconManager.get_icon("x"))
        self.btn_clear_file.setObjectName("btn_delete")
        self.btn_clear_file.setFixedWidth(36)
        self.btn_clear_file.setVisible(False)

        attach_layout.addWidget(self.lbl_attachment, 1)
        attach_layout.addWidget(self.btn_select_file)
        attach_layout.addWidget(self.btn_clear_file)

        form.addRow("PDF-Anhang:", attach_widget)
        card_layout.addLayout(form)

        self.btn_save = QtWidgets.QPushButton(" Bewegung speichern")
        self.btn_save.setIcon(IconManager.get_icon("save"))
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setMinimumHeight(44)
        card_layout.addWidget(self.btn_save)

        layout.addWidget(card)
        layout.addStretch()

        self.btn_save.clicked.connect(self.save)
        self.btn_select_file.clicked.connect(self.select_attachment)
        self.btn_clear_file.clicked.connect(self.clear_attachment)
        self.cb_typ.currentIndexChanged.connect(self.update_visibility)
        self.cb_depot.currentIndexChanged.connect(self.refresh_praeparate_for_depot)

        self.refresh_depots()
        self.refresh_praeparate_for_depot()
        self.update_visibility()

    def refresh_depots(self):
        self.cb_depot.clear()
        depots = self.db.list_depots()
        for d in depots:
            self.cb_depot.addItem(d[1], d[0])

    def refresh_praeparate_for_depot(self):
        self.cb_praeparat.clear()
        if self.cb_depot.count() == 0:
            return
        depot_id = self.cb_depot.currentData()
        assigned_ids = self.db.get_assigned_praeparate(depot_id)
        prae_list = self.db.list_praeparate()
        for pid, pname in prae_list:
            if not assigned_ids or pid in assigned_ids:
                self.cb_praeparat.addItem(pname, pid)

    def update_visibility(self):
        typ = self.cb_typ.currentText()
        self.d_eingang.setEnabled(typ == "Zugang")
        self.d_ausgang.setEnabled(typ in ("Abgang", "Vernichtung"))
        self.e_empfaenger.setEnabled(typ == "Abgang")

    def select_attachment(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "PDF-Datei auswählen", "", "PDF-Dateien (*.pdf);;Alle Dateien (*)"
        )
        if file_path:
            self.attachment_file = file_path
            filename = os.path.basename(file_path)
            if len(filename) > 35:
                filename = filename[:32] + "..."
            self.lbl_attachment.setText(f"{filename}")
            self.lbl_attachment.setProperty("hasFile", "true")
            self.lbl_attachment.style().unpolish(self.lbl_attachment)
            self.lbl_attachment.style().polish(self.lbl_attachment)
            self.btn_clear_file.setVisible(True)

    def clear_attachment(self):
        self.attachment_file = None
        self.lbl_attachment.setText("Keine Datei ausgewählt")
        self.lbl_attachment.setProperty("hasFile", "false")
        self.lbl_attachment.style().unpolish(self.lbl_attachment)
        self.lbl_attachment.style().polish(self.lbl_attachment)
        self.btn_clear_file.setVisible(False)

    def save(self):
        if self.security and not self.security.has_permission("movements_write"):
            QtWidgets.QMessageBox.warning(self, "Keine Berechtigung", "Keine Schreibberechtigung für Bewegungen.")
            return
        if self.cb_depot.count() == 0 or self.cb_praeparat.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Hinweis", "Bitte Depot und Präparat anlegen/zuordnen.")
            return

        depot_id = self.cb_depot.currentData()
        if self.security and not self.security.has_depot_access(int(depot_id), write=True):
            QtWidgets.QMessageBox.warning(self, "Keine Berechtigung", "Sie dürfen in dieses Depot nicht schreiben.")
            return
        prae_id = self.cb_praeparat.currentData()
        charge = self.e_charge.text().strip()
        verfall = to_iso(self.d_verfall.date())
        typ = self.cb_typ.currentText()
        eingang = to_iso(self.d_eingang.date()) if typ == "Zugang" else None
        ausgang = to_iso(self.d_ausgang.date()) if typ in ("Abgang", "Vernichtung") else None
        empfaenger = self.e_empfaenger.text().strip() if typ == "Abgang" else None
        anzahl = int(self.spin_anzahl.value())

        if not (charge and verfall and anzahl > 0):
            QtWidgets.QMessageBox.warning(self, "Fehlende Angaben", "Bitte Charge, Verfall und Anzahl angeben.")
            return

        last_id = self.db.insert_bewegung(depot_id, prae_id, charge, verfall, eingang, ausgang, empfaenger, anzahl, typ)

        if self.attachment_file:
            try:
                depot_name = self.db.get_depot_name(depot_id)
                saved_path = self.db.link_bewegung_with_attachment(
                    last_id, self.attachment_file, self.attachment_base_folder, depot_name
                )
                msg = f"✅ Bewegung mit Anhang gespeichert!\n\nDatei: {os.path.basename(saved_path)}"
            except Exception as e:
                msg = f"Bewegung gespeichert, aber Anhang-Fehler:\n{e}"
                QtWidgets.QMessageBox.warning(self, "Warnung", msg)
                return
        else:
            msg = "✅ Bewegung erfolgreich gespeichert!"

        QtWidgets.QMessageBox.information(self, "Gespeichert", msg)

        self.e_charge.clear()
        self.e_empfaenger.clear()
        self.spin_anzahl.setValue(1)
        self.clear_attachment()


