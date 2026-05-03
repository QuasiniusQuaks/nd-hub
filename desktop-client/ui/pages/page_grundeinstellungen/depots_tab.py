"""Depots-Verwaltung - CRUD für Depots."""
from PySide6 import QtWidgets
from db_manager import Database, fill_table
from icon_manager import IconManager
from ui.utils import create_card_widget
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog




class DepotsPage(QtWidgets.QWidget):
    def __init__(self, db: Database, security=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.security = security
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        title = QtWidgets.QLabel("Depots verwalten")
        title.setProperty("class", "page-title")
        layout.addWidget(title)
        
        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)
        
        self.table = QtWidgets.QTableWidget()
        self.table.setAlternatingRowColors(True)
        card_layout.addWidget(self.table)
        
        btns = QtWidgets.QHBoxLayout()
        btns.setSpacing(12)
        self.btn_add = QtWidgets.QPushButton("Neues Depot")
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
        
        self.btn_add.clicked.connect(self.add_depot)
        self.btn_edit.clicked.connect(self.edit_depot)
        self.btn_delete.clicked.connect(self.delete_depot)
        
        self.refresh()

    def refresh(self):
        rows = self.db.list_depots()
        display = [
            (r["id"], r["name"], r["adresse"] or "", r["telefon"] or "", r["email"] or "", r["institution_id"])
            for r in rows
        ]
        data = [("ID", "Name", "Adresse", "Telefon", "E-Mail", "Institution-ID")] + display
        fill_table(self.table, data)
        self.table.setColumnHidden(0, True)

    def add_depot(self):
        if self.security and not self.security.has_permission("masterdata_write"):
            QtWidgets.QMessageBox.warning(self, "Keine Berechtigung", "Keine Schreibberechtigung für Stammdaten.")
            return
        from ui.dialogs.basic_dialogs import DepotDialog
        dlg = DepotDialog(self)
        if exec_embedded_dialog(self, dlg) == QtWidgets.QDialog.Accepted:
            name, addr, tel, email = dlg.values()
            self.db.add_depot(name, addr, tel, email)
            self.refresh()

    def edit_depot(self):
        if self.security and not self.security.has_permission("masterdata_write"):
            QtWidgets.QMessageBox.warning(self, "Keine Berechtigung", "Keine Schreibberechtigung für Stammdaten.")
            return
        row = self.table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Bitte einen Depot-Eintrag auswählen.")
            return
        depot_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()
        addr = self.table.item(row, 2).text()
        tel = self.table.item(row, 3).text()
        email = self.table.item(row, 4).text()
        from ui.dialogs.basic_dialogs import DepotDialog
        dlg = DepotDialog(self, name, addr, tel, email)
        if exec_embedded_dialog(self, dlg) == QtWidgets.QDialog.Accepted:
            name, addr, tel, email = dlg.values()
            self.db.update_depot(depot_id, name, addr, tel, email)
            self.refresh()

    def delete_depot(self):
        if self.security and not self.security.has_permission("masterdata_write"):
            QtWidgets.QMessageBox.warning(self, "Keine Berechtigung", "Keine Schreibberechtigung für Stammdaten.")
            return
        row = self.table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Bitte einen Depot-Eintrag auswählen.")
            return
        depot_id = int(self.table.item(row, 0).text())
        if QtWidgets.QMessageBox.question(self, "Bestätigen", "Depot wirklich löschen?") == QtWidgets.QMessageBox.Yes:
            self.db.delete_depot(depot_id)
            self.refresh()
