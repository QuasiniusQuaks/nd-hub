"""Legacy-Kompatibilitaet fuer Benutzerverwaltung.

Die eigentliche Benutzerverwaltung laeuft als integrierte Seite in den
Grundeinstellungen (`UserManagementPage`). Dieses Modul bleibt fuer alte
Importpfade erhalten und bettet die neue Seite in einen Dialog ein.
"""

from PySide6 import QtWidgets

from ui.pages.page_grundeinstellungen.user_management_tab import UserManagementPage
from ui.pages.page_grundeinstellungen.user_management_dialogs import (
    AddUserDialog,
    EditUserDialog,
)


class UserManagementDialog(QtWidgets.QDialog):
    """Legacy-Dialog, der intern die neue integrierte Seite rendert."""

    def __init__(self, security_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benutzerverwaltung")
        self.resize(980, 680)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.page = UserManagementPage(security_manager, self)
        layout.addWidget(self.page)

        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch()
        btn_close = QtWidgets.QPushButton("Schliessen")
        btn_close.setMinimumHeight(40)
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)

