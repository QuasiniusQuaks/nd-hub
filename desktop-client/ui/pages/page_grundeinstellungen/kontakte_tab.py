"""Kontakte-Verwaltung - CRUD für Ansprechpartner pro Depot."""
from PySide6 import QtWidgets

from db_manager import Database, fill_table
from icon_manager import IconManager
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog
from ui.utils import create_card_widget


class KontaktePage(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QtWidgets.QLabel("Ansprechpartner verwalten")
        title.setProperty("class", "page-title")
        layout.addWidget(title)

        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(12)
        lbl_depot = QtWidgets.QLabel("Depot:")
        lbl_depot.setStyleSheet("font-weight: 600;")
        self.cb_depot = QtWidgets.QComboBox()
        self.cb_depot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        top.addWidget(lbl_depot)
        top.addWidget(self.cb_depot, 1)
        top.addStretch()
        card_layout.addLayout(top)

        self.table = QtWidgets.QTableWidget()
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        card_layout.addWidget(self.table)

        btns = QtWidgets.QHBoxLayout()
        btns.setSpacing(12)
        self.btn_add = QtWidgets.QPushButton("Neuer Ansprechpartner")
        self.btn_add.setIcon(IconManager.get_icon("add"))
        self.btn_add.setObjectName("btn_add")
        self.btn_edit = QtWidgets.QPushButton("Bearbeiten")
        self.btn_edit.setIcon(IconManager.get_icon("edit"))
        self.btn_delete = QtWidgets.QPushButton("Löschen")
        self.btn_delete.setIcon(IconManager.get_icon("delete"))
        self.btn_delete.setObjectName("btn_delete")
        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_delete)
        btns.addStretch()
        card_layout.addLayout(btns)

        layout.addWidget(card)

        self.btn_add.clicked.connect(self.add_kontakt)
        self.btn_edit.clicked.connect(self.edit_kontakt)
        self.btn_delete.clicked.connect(self.delete_kontakt)
        self.cb_depot.currentIndexChanged.connect(self.refresh)

        self.refresh_depots()
        self.refresh()

    def refresh_depots(self):
        self.cb_depot.clear()
        depots = self.db.list_depots()
        for d in depots:
            self.cb_depot.addItem(d[1], d[0])

    def refresh(self):
        if self.cb_depot.count() == 0:
            return
        depot_id = self.cb_depot.currentData()
        rows = self.db.list_kontakte(depot_id)
        data = [("ID", "Name", "Rolle", "Telefon", "E-Mail")] + rows
        fill_table(self.table, data)
        self.table.setColumnHidden(0, True)

    def add_kontakt(self):
        from ui.dialogs.basic_dialogs import KontaktDialog
        if self.cb_depot.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Hinweis", "Bitte zuerst ein Depot anlegen.")
            return
        depot_id = self.cb_depot.currentData()
        dlg = KontaktDialog(self)
        if exec_embedded_dialog(self, dlg) == QtWidgets.QDialog.Accepted:
            name, rolle, tel, email = dlg.values()
            self.db.add_kontakt(depot_id, name, rolle, tel, email)
            self.refresh()

    def edit_kontakt(self):
        row = self.table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Bitte einen Ansprechpartner auswählen.")
            return
        kontakt_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()
        rolle = self.table.item(row, 2).text()
        tel = self.table.item(row, 3).text()
        email = self.table.item(row, 4).text()
        from ui.dialogs.basic_dialogs import KontaktDialog
        dlg = KontaktDialog(self, name, rolle, tel, email)
        if exec_embedded_dialog(self, dlg) == QtWidgets.QDialog.Accepted:
            name, rolle, tel, email = dlg.values()
            self.db.update_kontakt(kontakt_id, name, rolle, tel, email)
            self.refresh()

    def delete_kontakt(self):
        row = self.table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Bitte einen Ansprechpartner auswählen.")
            return
        kontakt_id = int(self.table.item(row, 0).text())
        if QtWidgets.QMessageBox.question(self, "Bestätigen", "Ansprechpartner wirklich löschen?") == QtWidgets.QMessageBox.Yes:
            self.db.delete_kontakt(kontakt_id)
            self.refresh()
