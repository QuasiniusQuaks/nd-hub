"""Backend/sync operating mode step."""
from __future__ import annotations

from PySide6 import QtWidgets


class BackendStepMixin:
    """Issue #67: backend/sync step extracted from setup_wizard_dialog monolith."""

    def _build_backend_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        hint = QtWidgets.QLabel(
            "Wählen Sie zuerst den Betriebsmodus wie im Sync-Tab. "
            "Bei local_only wird Geokodierung übersprungen."
        )
        hint.setWordWrap(True)
        lay.addWidget(hint)
        form = QtWidgets.QFormLayout()
        self._sync_mode_combo = QtWidgets.QComboBox()
        self._sync_mode_combo.addItem("Nur lokal (local_only)", "local_only")
        self._sync_mode_combo.addItem("Hybrid Sync (hybrid_sync)", "hybrid_sync")
        self._sync_mode_combo.addItem("Nur Remote (remote_only)", "remote_only")
        form.addRow("Betriebsmodus:", self._sync_mode_combo)
        self._sync_backend_url_input = QtWidgets.QLineEdit()
        self._sync_backend_url_input.setPlaceholderText("http://127.0.0.1:8000")
        form.addRow("Backend-URL:", self._sync_backend_url_input)
        self._sync_backend_token_input = QtWidgets.QLineEdit()
        self._sync_backend_token_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self._sync_backend_token_input.setPlaceholderText("Bearer Token aus Web-App")
        form.addRow("Backend-Token:", self._sync_backend_token_input)
        lay.addLayout(form)
        self._sync_mode_combo.currentIndexChanged.connect(self._update_backend_mode_visibility)
        lay.addStretch()
        return w

    def _load_backend_config_into_ui(self) -> None:
        host = self.window()
        cfg = getattr(host, "config", None)
        if cfg is None:
            return
        mode = str(getattr(cfg, "get_operating_mode", lambda: "local_only")() or "local_only").strip().lower()
        idx = self._sync_mode_combo.findData(mode)
        self._sync_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._sync_backend_url_input.setText(str(getattr(cfg, "get_backend_url", lambda: "")() or "").strip())
        self._sync_backend_token_input.setText(str(getattr(cfg, "get_backend_token", lambda: "")() or "").strip())
        self._update_backend_mode_visibility()

    def _persist_backend_config(self) -> None:
        host = self.window()
        cfg = getattr(host, "config", None)
        if cfg is None:
            return
        mode = self._current_operating_mode()
        getattr(cfg, "set_operating_mode", lambda _: None)(mode)
        getattr(cfg, "set_backend_url", lambda _: None)(self._sync_backend_url_input.text().strip())
        getattr(cfg, "set_backend_token", lambda _: None)(self._sync_backend_token_input.text().strip())

    def _current_operating_mode(self) -> str:
        return str(self._sync_mode_combo.currentData() or "local_only")

    def _update_backend_mode_visibility(self) -> None:
        local_only = self._current_operating_mode() == "local_only"
        self._sync_backend_url_input.setEnabled(not local_only)
        self._sync_backend_token_input.setEnabled(not local_only)

    def _validate_backend_setup(self) -> bool:
        mode = self._current_operating_mode()
        if mode == "local_only":
            return True
        if not self._sync_backend_url_input.text().strip():
            self._show_error("Bitte Backend-URL für Hybrid/Remote angeben.")
            return False
        return True


