"""Integrierte Benutzerverwaltung als Tab in den Grundeinstellungen."""
import os

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtCore, QtWidgets

from ui.dialogs.embedded_dialog_host import exec_embedded_dialog, get_text_embedded
from ui.utils import configure_responsive_table

from .user_management_dialogs import AddUserDialog, EditUserDialog


class UserManagementPage(QtWidgets.QWidget):
    def __init__(self, security_manager, parent=None):
        super().__init__(parent)
        self.security = security_manager
        self._setup_ui()
        self.refresh_users()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QtWidgets.QLabel("Benutzerverwaltung")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        self.current_user_label = QtWidgets.QLabel()
        layout.addWidget(self.current_user_label)
        self._apply_user_mgmt_muted_style()

        toolbar = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton(" Benutzer hinzufügen")
        self.btn_add.setIcon(IconManager.get_icon("add"))
        self.btn_add.setObjectName("btn_add")
        self.btn_add.setProperty("requires_write", True)
        self.btn_add.clicked.connect(self.add_user)
        toolbar.addWidget(self.btn_add)

        self.btn_edit = QtWidgets.QPushButton(" Bearbeiten")
        self.btn_edit.setIcon(IconManager.get_icon("edit"))
        self.btn_edit.setObjectName("btn_secondary")
        self.btn_edit.setProperty("requires_write", True)
        self.btn_edit.clicked.connect(self.edit_user)
        toolbar.addWidget(self.btn_edit)

        self.btn_reset_password = QtWidgets.QPushButton(" Passwort zurücksetzen")
        self.btn_reset_password.setIcon(IconManager.get_icon("key"))
        self.btn_reset_password.setObjectName("btn_secondary")
        self.btn_reset_password.setProperty("requires_write", True)
        self.btn_reset_password.clicked.connect(self.reset_password)
        toolbar.addWidget(self.btn_reset_password)

        self.btn_unlock = QtWidgets.QPushButton(" Entsperren")
        self.btn_unlock.setIcon(IconManager.get_icon("refresh_ccw"))
        self.btn_unlock.setObjectName("btn_secondary")
        self.btn_unlock.setProperty("requires_write", True)
        self.btn_unlock.clicked.connect(self.unlock_user)
        toolbar.addWidget(self.btn_unlock)

        self.btn_delete = QtWidgets.QPushButton(" Löschen")
        self.btn_delete.setIcon(IconManager.get_icon("delete", color="#d32f2f"))
        self.btn_delete.setObjectName("btn_delete")
        self.btn_delete.setProperty("requires_write", True)
        self.btn_delete.clicked.connect(self.delete_user)
        toolbar.addWidget(self.btn_delete)

        self.btn_set_avatar = QtWidgets.QPushButton(" Profilbild setzen")
        self.btn_set_avatar.setIcon(IconManager.get_icon("folder"))
        self.btn_set_avatar.setObjectName("btn_secondary")
        self.btn_set_avatar.setProperty("requires_write", True)
        self.btn_set_avatar.clicked.connect(self.set_avatar_for_selected_user)
        toolbar.addWidget(self.btn_set_avatar)

        self.btn_clear_avatar = QtWidgets.QPushButton(" Profilbild entfernen")
        self.btn_clear_avatar.setIcon(IconManager.get_icon("x"))
        self.btn_clear_avatar.setObjectName("btn_secondary")
        self.btn_clear_avatar.setProperty("requires_write", True)
        self.btn_clear_avatar.clicked.connect(self.clear_avatar_for_selected_user)
        toolbar.addWidget(self.btn_clear_avatar)
        toolbar.addStretch()

        self.btn_refresh = QtWidgets.QPushButton("")
        self.btn_refresh.setIcon(IconManager.get_icon("refresh"))
        self.btn_refresh.setObjectName("btn_secondary")
        self.btn_refresh.setFixedWidth(40)
        self.btn_refresh.clicked.connect(self.refresh_users)
        toolbar.addWidget(self.btn_refresh)
        layout.addLayout(toolbar)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Benutzername", "Rolle", "E-Mail", "Erstellt", "Letzter Login", "Status", "Gesperrt", "Rechte", "Profilbild"]
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.update_button_states)
        configure_responsive_table(self.table, stretch_columns=[1, 3, 8], content_columns=[0, 2, 4, 5, 6, 7, 9])
        self.table.setColumnHidden(0, True)
        layout.addWidget(self.table)

        self.update_button_states()

    def _apply_user_mgmt_muted_style(self) -> None:
        c = AppleTheme.current_colors()
        self.current_user_label.setStyleSheet(
            f"font-size: 12px; color: {c['secondary_label']};"
        )

    def refresh_theme(self) -> None:
        self._apply_user_mgmt_muted_style()

    def _toast(self, message: str, level: str = "info"):
        host = self.window()
        if hasattr(host, "show_toast"):
            host.show_toast(message, level)

    def refresh_users(self):
        self.current_user_label.setText(
            f"Angemeldet als: {self.security.get_current_user()} ({self.security.get_current_role()})"
        )
        users = self.security.list_users()
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            # Backward-/forward-kompatibel
            if len(user) < 7:
                continue
            user_id = user[0]
            username = user[1]
            role = user[2]
            email = user[3]
            created_at = user[4]
            last_login = user[5]
            is_active = user[6]
            failed_attempts = int(user[7]) if len(user) > 7 and user[7] is not None else 0
            locked_until = user[8] if len(user) > 8 else None
            permissions_raw = user[10] if len(user) > 10 else ""
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(user_id)))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(username))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(role))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(email or "-"))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(created_at[:10] if created_at else "-"))
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(last_login[:16] if last_login else "Nie"))
            status = QtWidgets.QTableWidgetItem("Aktiv" if is_active else "Deaktiviert")
            if not is_active:
                status.setForeground(QtCore.Qt.red)
            self.table.setItem(row, 6, status)
            locked_state = "Ja" if locked_until else "Nein"
            if locked_until or failed_attempts >= 5:
                locked_state = f"Ja ({failed_attempts})"
            self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(locked_state))
            permissions_text = str(permissions_raw or "").strip()
            self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(permissions_text or "-"))

            avatar_path = self.security.get_user_avatar_path(user_id)
            avatar_state = "Ja" if avatar_path and os.path.exists(avatar_path) else "Nein"
            avatar_item = QtWidgets.QTableWidgetItem(avatar_state)
            if avatar_state == "Ja":
                avatar_item.setForeground(QtCore.Qt.darkGreen)
            self.table.setItem(row, 9, avatar_item)
        self.table.setColumnHidden(0, True)
        self.update_button_states()

    def update_button_states(self):
        has_selection = self.table.currentRow() >= 0
        host = self.window()
        read_only = bool(getattr(getattr(host, "db", None), "is_read_only_mode", lambda: False)())
        self.btn_add.setEnabled(not read_only)
        self.btn_edit.setEnabled(has_selection and not read_only)
        self.btn_delete.setEnabled(has_selection and not read_only)
        self.btn_reset_password.setEnabled(has_selection and not read_only)
        self.btn_unlock.setEnabled(has_selection and not read_only)
        self.btn_set_avatar.setEnabled(has_selection and not read_only)
        self.btn_clear_avatar.setEnabled(has_selection and not read_only)

    def _selected_user(self):
        row = self.table.currentRow()
        if row < 0:
            return None, None
        return int(self.table.item(row, 0).text()), self.table.item(row, 1).text()

    def add_user(self):
        dialog = AddUserDialog(self.security, self)
        if exec_embedded_dialog(self, dialog) == QtWidgets.QDialog.Accepted:
            username, password, role, email = dialog.get_user_data()
            success, message = self.security.create_user(username, password, role, email)
            QtWidgets.QMessageBox.information(self, "Erfolg" if success else "Fehler", message)
            if success:
                self._toast("Benutzer erfolgreich angelegt.", "success")
                self.refresh_users()

    def edit_user(self):
        user_id, _ = self._selected_user()
        if not user_id:
            return
        row = self.table.currentRow()
        username = self.table.item(row, 1).text()
        role = self.table.item(row, 2).text()
        email = self.table.item(row, 3).text()
        if email == "-":
            email = ""
        is_active = self.table.item(row, 6).text() == "Aktiv"
        dialog = EditUserDialog(username, role, email, is_active, self)
        if exec_embedded_dialog(self, dialog) == QtWidgets.QDialog.Accepted:
            new_username, new_role, new_email, new_is_active = dialog.get_user_data()
            success, message = self.security.update_user(
                user_id, new_username, new_role, new_email, new_is_active
            )
            QtWidgets.QMessageBox.information(self, "Erfolg" if success else "Fehler", message)
            if success:
                self._toast("Benutzerdaten aktualisiert.", "success")
                self.refresh_users()

    def reset_password(self):
        user_id, username = self._selected_user()
        if not user_id:
            return
        new_password, ok = get_text_embedded(
            self,
            "Neues Passwort",
            f"Neues Passwort für '{username}':",
            QtWidgets.QLineEdit.Password,
        )
        if not ok or not new_password:
            return
        confirm, ok = get_text_embedded(
            self,
            "Passwort bestätigen",
            "Passwort wiederholen:",
            QtWidgets.QLineEdit.Password,
        )
        if not ok or confirm != new_password:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Die Passwörter stimmen nicht überein.")
            return
        success, message = self.security.reset_password(user_id, new_password)
        QtWidgets.QMessageBox.information(self, "Erfolg" if success else "Fehler", message)
        if success:
            self._toast("Passwort wurde zurückgesetzt.", "success")

    def delete_user(self):
        user_id, username = self._selected_user()
        if not user_id:
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Benutzer löschen",
            f"Möchten Sie den Benutzer '{username}' wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        success, message = self.security.delete_user(user_id)
        QtWidgets.QMessageBox.information(self, "Erfolg" if success else "Fehler", message)
        if success:
            self._toast("Benutzer gelöscht.", "success")
            self.refresh_users()

    def unlock_user(self):
        user_id, username = self._selected_user()
        if not user_id:
            return
        success, message = self.security.unlock_user(user_id)
        QtWidgets.QMessageBox.information(self, "Erfolg" if success else "Fehler", message)
        if success:
            self._toast(f"Benutzer '{username}' entsperrt.", "success")
            self.refresh_users()

    def _refresh_sidebar_avatar_if_needed(self, affected_user_id: int):
        current_user_id = self.security.get_current_user_id()
        if current_user_id != affected_user_id:
            return
        host = self.window()
        if hasattr(host, "_update_user_avatar_display"):
            host._update_user_avatar_display()

    def set_avatar_for_selected_user(self):
        user_id, username = self._selected_user()
        if not user_id:
            return
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            f"Profilbild für {username} auswählen",
            "",
            "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not file_path:
            return
        success, message = self.security.set_user_avatar(user_id, file_path)
        QtWidgets.QMessageBox.information(self, "Profilbild" if success else "Fehler", message)
        if success:
            self._toast("Profilbild gespeichert.", "success")
            self.refresh_users()
            self._refresh_sidebar_avatar_if_needed(user_id)

    def clear_avatar_for_selected_user(self):
        user_id, username = self._selected_user()
        if not user_id:
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Profilbild entfernen",
            f"Soll das Profilbild von '{username}' entfernt werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        success, message = self.security.clear_user_avatar(user_id)
        QtWidgets.QMessageBox.information(self, "Profilbild" if success else "Fehler", message)
        if success:
            self._toast("Profilbild entfernt.", "success")
            self.refresh_users()
            self._refresh_sidebar_avatar_if_needed(user_id)
