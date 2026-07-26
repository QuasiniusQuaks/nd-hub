from __future__ import annotations

from apple_theme import AppleTheme
from core.data_access_layer import BackendApiClient, BackendSyncConfig
from PySide6 import QtWidgets

from ui.utils import configure_responsive_table


class AuditLogsPage(QtWidgets.QWidget):
    def __init__(self, config_provider, parent=None):
        super().__init__(parent)
        self._config_provider = config_provider
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Audit-Logs")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {AppleTheme.current_colors()['label']};")
        layout.addWidget(title)

        filter_row = QtWidgets.QHBoxLayout()
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Benutzername (optional)")
        filter_row.addWidget(self.username_input)
        self.action_input = QtWidgets.QLineEdit()
        self.action_input.setPlaceholderText("Aktion (optional)")
        filter_row.addWidget(self.action_input)
        self.page_spin = QtWidgets.QSpinBox()
        self.page_spin.setRange(1, 9999)
        self.page_spin.setValue(1)
        filter_row.addWidget(self.page_spin)
        self.btn_load = QtWidgets.QPushButton("Laden")
        self.btn_load.setObjectName("btn_secondary")
        self.btn_load.clicked.connect(self.refresh_logs)
        filter_row.addWidget(self.btn_load)
        layout.addLayout(filter_row)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Zeit", "User", "Aktion", "Entity", "Entity-ID", "Details"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        configure_responsive_table(self.table, stretch_columns=[5], content_columns=[0, 1, 2, 3, 4])
        layout.addWidget(self.table)

        self.status_label = QtWidgets.QLabel("Noch nicht geladen.")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {AppleTheme.current_colors()['secondary_label']};")
        layout.addWidget(self.status_label)

    def _get_client(self) -> BackendApiClient:
        config = self._config_provider() if callable(self._config_provider) else None
        if config is None:
            raise RuntimeError("Konfiguration nicht verfuegbar")
        base_url = str(getattr(config, "get_backend_url", lambda: "")() or "").strip()
        token = str(getattr(config, "get_backend_token", lambda: "")() or "").strip()
        return BackendApiClient(BackendSyncConfig(base_url=base_url, access_token=token))

    def refresh_logs(self):
        try:
            client = self._get_client()
            payload = client.get_audit_logs(
                username=self.username_input.text().strip(),
                action=self.action_input.text().strip(),
                page=int(self.page_spin.value()),
                page_size=100,
            )
            rows = payload.get("items") or payload.get("logs") or []
            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(row.get("created_at") or row.get("timestamp") or "")))
                self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(row.get("username") or "")))
                self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(row.get("action") or "")))
                self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(row.get("entity_name") or "")))
                self.table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(row.get("entity_id") or "")))
                self.table.setItem(r, 5, QtWidgets.QTableWidgetItem(str(row.get("details") or "")))
            self.status_label.setText(f"{len(rows)} Eintraege geladen.")
        except Exception as exc:
            self.status_label.setText(f"Audit-Logs konnten nicht geladen werden: {exc}")
