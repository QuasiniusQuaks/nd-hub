"""Präparate-Verwaltung - CRUD für Präparate."""
from PySide6 import QtWidgets

from apple_theme import AppleTheme
from db_manager import Database, fill_table
from icon_manager import IconManager
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog
from ui.utils import create_card_widget


class PraeparatDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent=None,
        *,
        name: str = "",
        wirkstoff: str = "",
        darreichungsform: str = "",
        staerke: str = "",
        einheit: str = "",
        pzn: str = "",
        hersteller: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("Präparat")
        self.setMinimumWidth(480)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.e_name = QtWidgets.QLineEdit(name)
        self.e_wirkstoff = QtWidgets.QLineEdit(wirkstoff)
        self.e_darreichungsform = QtWidgets.QLineEdit(darreichungsform)
        self.e_staerke = QtWidgets.QLineEdit(staerke)
        self.e_einheit = QtWidgets.QLineEdit(einheit)
        self.e_pzn = QtWidgets.QLineEdit(pzn)
        self.e_hersteller = QtWidgets.QLineEdit(hersteller)
        form.addRow("Name:", self.e_name)
        form.addRow("Wirkstoff:", self.e_wirkstoff)
        form.addRow("Darreichungsform:", self.e_darreichungsform)
        form.addRow("Stärke:", self.e_staerke)
        form.addRow("Einheit:", self.e_einheit)
        form.addRow("PZN:", self.e_pzn)
        form.addRow("Hersteller:", self.e_hersteller)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {
            "name": self.e_name.text().strip(),
            "wirkstoff": self.e_wirkstoff.text().strip(),
            "darreichungsform": self.e_darreichungsform.text().strip(),
            "staerke": self.e_staerke.text().strip(),
            "einheit": self.e_einheit.text().strip(),
            "pzn": self.e_pzn.text().strip(),
            "hersteller": self.e_hersteller.text().strip(),
        }


class PraeparatePage(QtWidgets.QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QtWidgets.QLabel("Präparate verwalten")
        title.setProperty("class", "page-title")
        layout.addWidget(title)

        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)

        self._info_muted = QtWidgets.QLabel("Der Sollbestand wird bei der Zuordnung zu Depots festgelegt.")
        self._apply_praeparate_info_style()
        card_layout.addWidget(self._info_muted)

        self.table = QtWidgets.QTableWidget()
        card_layout.addWidget(self.table)

        btns = QtWidgets.QHBoxLayout()
        btns.setSpacing(12)
        self.btn_add = QtWidgets.QPushButton("Neues Präparat")
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

        self.btn_add.clicked.connect(self.add_item)
        self.btn_edit.clicked.connect(self.edit_item)
        self.btn_delete.clicked.connect(self.delete_item)

        self.refresh()

    def _apply_praeparate_info_style(self) -> None:
        c = AppleTheme.current_colors()
        self._info_muted.setStyleSheet(
            f"color: {c['secondary_label']}; font-size: 12px; padding: 0 0 12px 0;"
        )

    def refresh_theme(self) -> None:
        self._apply_praeparate_info_style()

    def refresh(self):
        rows = self.db.list_praeparate_extended()
        data = [
            ("ID", "Name", "Wirkstoff", "Darreichungsform", "Stärke", "Einheit", "PZN", "Hersteller")
        ] + rows
        fill_table(self.table, data)
        self.table.setColumnHidden(0, True)

    def add_item(self):
        dlg = PraeparatDialog(self)
        if exec_embedded_dialog(self, dlg) == QtWidgets.QDialog.Accepted:
            payload = dlg.values()
            if not payload["name"]:
                QtWidgets.QMessageBox.warning(self, "Hinweis", "Der Name ist erforderlich.")
                return
            self.db.add_praeparat_extended(**payload)
            self.refresh()

    def edit_item(self):
        row = self.table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Bitte einen Präparat-Eintrag auswählen.")
            return
        prae_id = int(self.table.item(row, 0).text())
        dlg = PraeparatDialog(
            self,
            name=self.table.item(row, 1).text() if self.table.item(row, 1) else "",
            wirkstoff=self.table.item(row, 2).text() if self.table.item(row, 2) else "",
            darreichungsform=self.table.item(row, 3).text() if self.table.item(row, 3) else "",
            staerke=self.table.item(row, 4).text() if self.table.item(row, 4) else "",
            einheit=self.table.item(row, 5).text() if self.table.item(row, 5) else "",
            pzn=self.table.item(row, 6).text() if self.table.item(row, 6) else "",
            hersteller=self.table.item(row, 7).text() if self.table.item(row, 7) else "",
        )
        if exec_embedded_dialog(self, dlg) == QtWidgets.QDialog.Accepted:
            payload = dlg.values()
            if not payload["name"]:
                QtWidgets.QMessageBox.warning(self, "Hinweis", "Der Name ist erforderlich.")
                return
            self.db.update_praeparat_extended(prae_id=prae_id, **payload)
            self.refresh()

    def delete_item(self):
        row = self.table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Hinweis", "Bitte einen Präparat-Eintrag auswählen.")
            return
        prae_id = int(self.table.item(row, 0).text())
        if QtWidgets.QMessageBox.question(self, "Bestätigen", "Präparat wirklich löschen?") == QtWidgets.QMessageBox.Yes:
            self.db.delete_praeparat(prae_id)
            self.refresh()
