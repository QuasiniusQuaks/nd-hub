"""Sync-Monitoring-Tab für Grundeinstellungen (Issue #93)."""
from urllib import error, request
from urllib.parse import urlparse

from apple_theme import AppleTheme
from core.data_access_layer import BackendApiClient, BackendSyncConfig, OperatingMode
from icon_manager import IconManager
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from ui.utils import create_card_widget


def _require_http_scheme(url: str) -> str:
    """Validiert dass die URL nur http/https verwendet (SSRF-Schutz)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url


def create_sync_tab(self):
    """Erstellt Monitoring-Tab fuer Outbox/Sync-Zustand."""
    tab = QtWidgets.QWidget()
    outer_layout = QtWidgets.QVBoxLayout(tab)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    outer_layout.addWidget(scroll)

    content = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(16)
    scroll.setWidget(content)

    settings_card = create_card_widget()
    settings_layout = QtWidgets.QVBoxLayout(settings_card)
    settings_layout.setSpacing(10)
    settings_title = QtWidgets.QLabel("Desktop-Sync Konfiguration")
    settings_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {AppleTheme.current_colors()['label']};")
    settings_layout.addWidget(settings_title)
    settings_info = QtWidgets.QLabel(
        "Konfigurieren Sie hier Betriebsmodus, Backend-URL und Token fuer den Hybrid-Sync."
    )
    settings_info.setWordWrap(True)
    settings_info.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 13px;")
    settings_layout.addWidget(settings_info)

    form = QtWidgets.QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setSpacing(8)
    self.sync_mode_combo = QtWidgets.QComboBox()
    self.sync_mode_combo.addItem("Nur lokal (local_only)", "local_only")
    self.sync_mode_combo.addItem("Hybrid Sync (hybrid_sync)", "hybrid_sync")
    self.sync_mode_combo.addItem("Nur Remote (remote_only)", "remote_only")
    form.addRow("Betriebsmodus:", self.sync_mode_combo)

    self.sync_backend_url_input = QtWidgets.QLineEdit()
    self.sync_backend_url_input.setPlaceholderText("http://127.0.0.1:8000")
    form.addRow("Backend-URL:", self.sync_backend_url_input)

    self.sync_backend_token_input = QtWidgets.QLineEdit()
    self.sync_backend_token_input.setEchoMode(QtWidgets.QLineEdit.Password)
    self.sync_backend_token_input.setPlaceholderText("Bearer Token aus Web-App")
    form.addRow("Backend-Token:", self.sync_backend_token_input)
    settings_layout.addLayout(form)

    settings_actions = QtWidgets.QVBoxLayout()
    settings_actions.setSpacing(8)
    self.btn_sync_save_config = QtWidgets.QPushButton("Sync-Konfiguration speichern")
    self.btn_sync_save_config.setIcon(IconManager.get_icon("save"))
    self.btn_sync_save_config.setObjectName("btn_save")
    self.btn_sync_save_config.setMinimumHeight(38)
    settings_actions.addWidget(self.btn_sync_save_config)
    self.btn_sync_test_connection = QtWidgets.QPushButton("Backend-Verbindung testen")
    self.btn_sync_test_connection.setIcon(IconManager.get_icon("activity"))
    self.btn_sync_test_connection.setObjectName("btn_secondary")
    self.btn_sync_test_connection.setMinimumHeight(38)
    settings_actions.addWidget(self.btn_sync_test_connection)
    settings_layout.addLayout(settings_actions)

    self.sync_config_status_label = QtWidgets.QLabel("")
    self.sync_config_status_label.setStyleSheet(f"font-size: 12px; color: {AppleTheme.current_colors()['secondary_label']};")
    self.sync_config_status_label.setWordWrap(True)
    settings_layout.addWidget(self.sync_config_status_label)
    layout.addWidget(settings_card)

    token_card = create_card_widget()
    token_layout = QtWidgets.QVBoxLayout(token_card)
    token_layout.setSpacing(8)
    token_title = QtWidgets.QLabel("Desktop-Sync Tokens")
    token_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {AppleTheme.current_colors()['label']};")
    token_layout.addWidget(token_title)
    token_info = QtWidgets.QLabel("Erzeugt und verwaltet API-Tokens fuer Desktop-Hybrid-Sync.")
    token_info.setWordWrap(True)
    token_info.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 12px;")
    token_layout.addWidget(token_info)

    token_form = QtWidgets.QFormLayout()
    token_form.setContentsMargins(0, 0, 0, 0)
    token_form.setSpacing(8)
    self.sync_token_note_input = QtWidgets.QLineEdit()
    self.sync_token_note_input.setPlaceholderText("Notiz (optional)")
    token_form.addRow("Notiz:", self.sync_token_note_input)
    self.sync_token_hours_spin = QtWidgets.QSpinBox()
    self.sync_token_hours_spin.setRange(1, 24 * 30)
    self.sync_token_hours_spin.setValue(72)
    self.sync_token_hours_spin.setSuffix(" h")
    token_form.addRow("Gueltig:", self.sync_token_hours_spin)
    token_layout.addLayout(token_form)

    token_btn_row = QtWidgets.QHBoxLayout()
    self.btn_sync_create_token = QtWidgets.QPushButton("Token erzeugen")
    self.btn_sync_create_token.setObjectName("btn_save")
    self.btn_sync_create_token.setMinimumHeight(38)
    token_btn_row.addWidget(self.btn_sync_create_token)
    token_btn_row.addStretch()
    token_layout.addLayout(token_btn_row)

    self.sync_token_output = QtWidgets.QPlainTextEdit()
    self.sync_token_output.setReadOnly(True)
    self.sync_token_output.setPlaceholderText("Neuer Token wird hier angezeigt.")
    self.sync_token_output.setMinimumHeight(70)
    token_layout.addWidget(self.sync_token_output)

    self.table_sync_tokens = QtWidgets.QTableWidget()
    self.table_sync_tokens.setColumnCount(4)
    self.table_sync_tokens.setHorizontalHeaderLabels(["Token-ID", "Benutzer", "Ablauf", "Notiz"])
    self.table_sync_tokens.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    self.table_sync_tokens.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    self.table_sync_tokens.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    self.table_sync_tokens.setMinimumHeight(140)
    token_layout.addWidget(self.table_sync_tokens)

    token_actions = QtWidgets.QVBoxLayout()
    token_actions.setSpacing(8)
    self.btn_sync_refresh_tokens = QtWidgets.QPushButton("Tokens laden")
    self.btn_sync_refresh_tokens.setObjectName("btn_secondary")
    self.btn_sync_refresh_tokens.setMinimumHeight(38)
    token_actions.addWidget(self.btn_sync_refresh_tokens)
    self.btn_sync_revoke_token = QtWidgets.QPushButton("Ausgewaehlten Token widerrufen")
    self.btn_sync_revoke_token.setObjectName("btn_delete")
    self.btn_sync_revoke_token.setMinimumHeight(38)
    token_actions.addWidget(self.btn_sync_revoke_token)
    token_layout.addLayout(token_actions)
    layout.addWidget(token_card)

    card = create_card_widget()
    card_layout = QtWidgets.QVBoxLayout(card)
    card_layout.setSpacing(10)

    c = AppleTheme.current_colors()
    title = QtWidgets.QLabel("Synchronisation")
    title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']};")
    card_layout.addWidget(title)

    info = QtWidgets.QLabel(
        "Zeigt den Zustand der lokalen Sync-Outbox.\n"
        "Konflikte koennen erneut in die Retry-Warteschlange gestellt werden."
    )
    info.setWordWrap(True)
    info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px;")
    card_layout.addWidget(info)

    state_row = QtWidgets.QHBoxLayout()
    state_row.setSpacing(8)
    state_title = QtWidgets.QLabel("Status:")
    state_title.setStyleSheet(f"font-size: 13px; color: {c['secondary_label']};")
    state_row.addWidget(state_title)
    self.sync_state_badge = QtWidgets.QLabel("UNBEKANNT")
    self.sync_state_badge.setStyleSheet(
        "font-size: 11px; font-weight: 700; color: #ffffff; "
        "background-color: #6b7280; border-radius: 10px; padding: 2px 8px;"
    )
    state_row.addWidget(self.sync_state_badge)
    self.sync_state_hint = QtWidgets.QLabel("")
    self.sync_state_hint.setStyleSheet(f"font-size: 12px; color: {c['secondary_label']};")
    state_row.addWidget(self.sync_state_hint, 1)
    state_row.addStretch()
    card_layout.addLayout(state_row)

    self.sync_next_run_label = QtWidgets.QLabel("Auto-Sync: -")
    self.sync_next_run_label.setStyleSheet(f"font-size: 12px; color: {c['secondary_label']};")
    card_layout.addWidget(self.sync_next_run_label)

    self.sync_stats_label = QtWidgets.QLabel("-")
    self.sync_stats_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    self.sync_stats_label.setStyleSheet(f"font-size: 13px; color: {c['label']};")
    card_layout.addWidget(self.sync_stats_label)

    self.sync_remote_stats_label = QtWidgets.QLabel("Remote-Stats: -")
    self.sync_remote_stats_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    self.sync_remote_stats_label.setStyleSheet(f"font-size: 12px; color: {c['secondary_label']};")
    card_layout.addWidget(self.sync_remote_stats_label)

    actions = QtWidgets.QVBoxLayout()
    actions.setSpacing(8)
    self.btn_sync_refresh = QtWidgets.QPushButton("Status aktualisieren")
    self.btn_sync_refresh.setIcon(IconManager.get_icon("refresh_ccw"))
    self.btn_sync_refresh.setObjectName("btn_secondary")
    self.btn_sync_refresh.setMinimumHeight(38)
    actions.addWidget(self.btn_sync_refresh)

    self.btn_sync_retry_conflicts = QtWidgets.QPushButton("Konflikte erneut versuchen")
    self.btn_sync_retry_conflicts.setIcon(IconManager.get_icon("refresh_ccw"))
    self.btn_sync_retry_conflicts.setObjectName("btn_secondary")
    self.btn_sync_retry_conflicts.setMinimumHeight(38)
    actions.addWidget(self.btn_sync_retry_conflicts)

    self.btn_sync_run_now = QtWidgets.QPushButton("Jetzt synchronisieren")
    self.btn_sync_run_now.setIcon(IconManager.get_icon("activity"))
    self.btn_sync_run_now.setMinimumHeight(38)
    actions.addWidget(self.btn_sync_run_now)
    card_layout.addLayout(actions)

    layout.addWidget(card)
    layout.addStretch()

    self.btn_sync_refresh.clicked.connect(self.refresh_sync_status)
    self.btn_sync_retry_conflicts.clicked.connect(self.retry_sync_conflicts)
    self.btn_sync_run_now.clicked.connect(self.trigger_sync_now)
    self.btn_sync_save_config.clicked.connect(self.save_sync_configuration)
    self.btn_sync_test_connection.clicked.connect(self.test_sync_connection)
    self.btn_sync_create_token.clicked.connect(self.create_sync_token)
    self.btn_sync_refresh_tokens.clicked.connect(self.refresh_sync_tokens)
    self.btn_sync_revoke_token.clicked.connect(self.revoke_selected_sync_token)
    self.sync_schedule_timer = QtCore.QTimer(self)
    self.sync_schedule_timer.timeout.connect(self._update_sync_schedule_hint)
    self.sync_schedule_timer.start(1000)
    self.load_sync_configuration()
    self._update_sync_schedule_hint()
    self.refresh_sync_tokens()
    self._update_sync_tab_responsiveness()
    return tab


def _update_sync_tab_responsiveness(self) -> None:
    if not hasattr(self, "sync_page"):
        return
    compact = self.sync_page.width() < 980

    if hasattr(self, "btn_sync_save_config"):
        self.btn_sync_save_config.setText("Speichern" if compact else "Sync-Konfiguration speichern")
    if hasattr(self, "btn_sync_test_connection"):
        self.btn_sync_test_connection.setText("Verbindung testen" if compact else "Backend-Verbindung testen")
    if hasattr(self, "btn_sync_create_token"):
        self.btn_sync_create_token.setText("Token erstellen" if compact else "Token erzeugen")
    if hasattr(self, "btn_sync_refresh_tokens"):
        self.btn_sync_refresh_tokens.setText("Tokens neu laden" if compact else "Tokens laden")
    if hasattr(self, "btn_sync_revoke_token"):
        self.btn_sync_revoke_token.setText("Token widerrufen" if compact else "Ausgewaehlten Token widerrufen")
    if hasattr(self, "btn_sync_refresh"):
        self.btn_sync_refresh.setText("Aktualisieren" if compact else "Status aktualisieren")
    if hasattr(self, "btn_sync_retry_conflicts"):
        self.btn_sync_retry_conflicts.setText("Konflikte retry" if compact else "Konflikte erneut versuchen")
    if hasattr(self, "btn_sync_run_now"):
        self.btn_sync_run_now.setText("Jetzt syncen" if compact else "Jetzt synchronisieren")

    if hasattr(self, "table_sync_tokens"):
        self.table_sync_tokens.horizontalHeader().setStretchLastSection(True)
        if compact:
            self.table_sync_tokens.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
            self.table_sync_tokens.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.table_sync_tokens.setColumnWidth(0, 190)
            self.table_sync_tokens.setColumnWidth(1, 120)
            self.table_sync_tokens.setColumnWidth(2, 145)
        else:
            self.table_sync_tokens.resizeColumnsToContents()


def _get_host_config(self):
    host = self.window()
    return getattr(host, "config", None)


def load_sync_configuration(self) -> None:
    config = self._get_host_config()
    if config is None:
        self.sync_config_status_label.setText("Konfiguration im Hauptfenster nicht verfuegbar.")
        return
    mode = str(getattr(config, "get_operating_mode", lambda: "local_only")() or "local_only").strip().lower()
    mode_index = self.sync_mode_combo.findData(mode)
    if mode_index < 0:
        mode_index = self.sync_mode_combo.findData("local_only")
    if mode_index >= 0:
        self.sync_mode_combo.setCurrentIndex(mode_index)
    self.sync_backend_url_input.setText(str(getattr(config, "get_backend_url", lambda: "")() or "").strip())
    self.sync_backend_token_input.setText(str(getattr(config, "get_backend_token", lambda: "")() or "").strip())
    self.sync_config_status_label.setText("Aktuelle Sync-Konfiguration geladen.")


def save_sync_configuration(self) -> None:
    config = self._get_host_config()
    if config is None:
        QtWidgets.QMessageBox.warning(self, "Sync", "Konfiguration im Hauptfenster nicht verfuegbar.")
        return
    mode = str(self.sync_mode_combo.currentData() or "local_only").strip().lower()
    if mode not in {item.value for item in OperatingMode}:
        mode = "local_only"
    backend_url = self.sync_backend_url_input.text().strip()
    backend_token = self.sync_backend_token_input.text().strip()
    try:
        config.set_operating_mode(mode)
        config.set_backend_url(backend_url)
        config.set_backend_token(backend_token)
        host = self.window()
        if hasattr(host, "_init_data_access_layer"):
            host._init_data_access_layer()
        if hasattr(host, "_init_sync_service"):
            host._init_sync_service()
        if hasattr(host, "_refresh_sync_scheduler"):
            host._refresh_sync_scheduler()
        self.sync_config_status_label.setText("Konfiguration gespeichert. Sync-Service neu initialisiert.")
        self._toast("Sync-Konfiguration gespeichert.", "success")
        self.refresh_sync_status()
    except Exception as exc:
        QtWidgets.QMessageBox.critical(self, "Sync", f"Konfiguration konnte nicht gespeichert werden:\n{exc}")


def test_sync_connection(self) -> None:
    backend_url = self.sync_backend_url_input.text().strip()
    if not backend_url:
        self.sync_config_status_label.setText("Bitte zuerst eine Backend-URL eintragen.")
        return
    self.sync_config_status_label.setText("Pruefe Verbindung...")
    token = self.sync_backend_token_input.text().strip()
    try:
        client = BackendApiClient(BackendSyncConfig(base_url=backend_url, access_token=token))
        healthy = client.check_health()
        if not healthy:
            self.sync_config_status_label.setText("Backend nicht erreichbar oder Healthcheck fehlgeschlagen.")
            return
        me_info = "-"
        if token:
            try:
                req = request.Request(
                    _require_http_scheme(f"{backend_url.rstrip('/')}/auth/me"),
                    method="GET",
                    headers={"Authorization": f"Bearer {token}"},
                )
                with request.urlopen(req, timeout=4) as response:  # nosec B310: URL scheme validated by _require_http_scheme
                    if 200 <= response.status < 300:
                        me_info = "Token gueltig"
            except error.HTTPError as exc:
                me_info = f"Token-Check fehlgeschlagen ({exc.code})"
            except Exception:
                me_info = "Token-Check fehlgeschlagen"
        self.sync_config_status_label.setText(f"Backend erreichbar. {me_info}")
    except Exception as exc:
        self.sync_config_status_label.setText(f"Verbindungstest fehlgeschlagen: {exc}")


def _build_api_client_from_inputs(self) -> BackendApiClient:
    backend_url = self.sync_backend_url_input.text().strip()
    token = self.sync_backend_token_input.text().strip()
    if not backend_url:
        raise RuntimeError("Backend-URL ist leer.")
    return BackendApiClient(BackendSyncConfig(base_url=backend_url, access_token=token))


def refresh_sync_tokens(self) -> None:
    if not hasattr(self, "table_sync_tokens"):
        return
    self.table_sync_tokens.setRowCount(0)
    try:
        client = self._build_api_client_from_inputs()
        payload = client.list_sync_tokens()
        rows = payload.get("tokens") or payload.get("items") or []
        self.table_sync_tokens.setRowCount(len(rows))
        for r, row in enumerate(rows):
            token_id = str(row.get("id") or row.get("token_id") or "")
            username = str(row.get("username") or "")
            expires = str(row.get("expires_at") or row.get("expiresAt") or "-")
            note = str(row.get("note") or "")
            self.table_sync_tokens.setItem(r, 0, QtWidgets.QTableWidgetItem(token_id))
            self.table_sync_tokens.setItem(r, 1, QtWidgets.QTableWidgetItem(username))
            self.table_sync_tokens.setItem(r, 2, QtWidgets.QTableWidgetItem(expires))
            self.table_sync_tokens.setItem(r, 3, QtWidgets.QTableWidgetItem(note))
        self.table_sync_tokens.resizeColumnsToContents()
    except Exception as exc:
        self.sync_config_status_label.setText(f"Token-Liste konnte nicht geladen werden: {exc}")


def create_sync_token(self) -> None:
    if self._is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Token-Erstellung ist nur mit Schreibzugriff moeglich.")
        return
    host = self.window()
    username = ""
    if hasattr(host, "security") and hasattr(host.security, "get_current_user"):
        username = str(host.security.get_current_user() or "")
    if not username:
        username = "desktop-client"
    try:
        client = self._build_api_client_from_inputs()
        payload = client.create_sync_token(
            username=username,
            expires_in_hours=int(self.sync_token_hours_spin.value()),
            note=self.sync_token_note_input.text().strip(),
        )
        token_value = str(payload.get("token") or payload.get("access_token") or "")
        self.sync_token_output.setPlainText(token_value or "Token wurde erstellt, aber nicht im Response geliefert.")
        self._toast("Sync-Token erstellt.", "success")
        self.refresh_sync_tokens()
    except Exception as exc:
        QtWidgets.QMessageBox.critical(self, "Sync-Token", f"Token konnte nicht erstellt werden:\n{exc}")


def revoke_selected_sync_token(self) -> None:
    row = self.table_sync_tokens.currentRow() if hasattr(self, "table_sync_tokens") else -1
    if row < 0:
        QtWidgets.QMessageBox.information(self, "Sync-Token", "Bitte zuerst einen Token auswaehlen.")
        return
    token_id_item = self.table_sync_tokens.item(row, 0)
    token_id = token_id_item.text().strip() if token_id_item else ""
    if not token_id:
        return
    try:
        client = self._build_api_client_from_inputs()
        client.revoke_sync_token(token_id=token_id)
        self._toast("Sync-Token widerrufen.", "info")
        self.refresh_sync_tokens()
    except Exception as exc:
        QtWidgets.QMessageBox.critical(self, "Sync-Token", f"Token konnte nicht widerrufen werden:\n{exc}")


def refresh_sync_status(self) -> None:
    if not hasattr(self, "sync_stats_label"):
        return
    if not hasattr(self.db, "get_sync_outbox_stats"):
        self.sync_stats_label.setText("Outbox-Statistiken nicht verfuegbar.")
        self._set_sync_state_badge("UNBEKANNT", "#6b7280", "Keine Outbox-API vorhanden")
        return
    try:
        stats = self.db.get_sync_outbox_stats()
        counts = stats.get("counts", {})
        pending = int(counts.get("pending", 0))
        retry = int(counts.get("retry", 0))
        conflict = int(counts.get("conflict", 0))
        done = int(counts.get("done", 0))
        oldest = stats.get("oldest_pending_at")
        latest_success = stats.get("latest_success_at")
        latest_error = stats.get("latest_error") or {}
        lines = [
            f"Pending: {pending}",
            f"Retry: {retry}",
            f"Conflict: {conflict}",
            f"Done: {done}",
            f"Total: {int(counts.get('total', 0))}",
        ]
        if oldest:
            lines.append(f"Aeltester offener Eintrag: {oldest}")
        if latest_success:
            lines.append(f"Letzter erfolgreicher Sync: {latest_success}")
        if latest_error:
            error_status = str(latest_error.get("status") or "?").upper()
            error_at = str(latest_error.get("at") or "")
            error_message = str(latest_error.get("message") or "")
            if len(error_message) > 160:
                error_message = f"{error_message[:157]}..."
            lines.append(f"Letzter Fehler [{error_status}] ({error_at}): {error_message}")
        self.sync_stats_label.setText("\n".join(lines))
        self._refresh_remote_sync_stats()
        if conflict > 0:
            self._set_sync_state_badge("KRITISCH", "#dc2626", "Konflikte vorhanden")
        elif retry > 0:
            self._set_sync_state_badge("WARNUNG", "#d97706", "Retry-Eintraege vorhanden")
        elif pending > 0:
            self._set_sync_state_badge("AKTIV", "#f59e0b", "Pending-Eintraege werden synchronisiert")
        elif done > 0:
            self._set_sync_state_badge("OK", "#16a34a", "Letzte Synchronisation erfolgreich")
        else:
            self._set_sync_state_badge("LEER", "#2563eb", "Noch keine Sync-Aktivitaet")
    except Exception as exc:
        self.sync_stats_label.setText(f"Fehler beim Laden der Sync-Statistik: {exc}")
        self._set_sync_state_badge("FEHLER", "#dc2626", "Status konnte nicht geladen werden")
    self._update_sync_schedule_hint()


def _refresh_remote_sync_stats(self) -> None:
    if not hasattr(self, "sync_remote_stats_label"):
        return
    try:
        client = self._build_api_client_from_inputs()
        status_payload = client.get_sync_status()
        ops_payload = client.get_sync_ops_stats()
        status_text = str(status_payload.get("status") or status_payload.get("effective_mode") or "-")
        queued = int(status_payload.get("queued") or status_payload.get("pending") or 0)
        failed = int(status_payload.get("failed") or 0)
        pushed = int(ops_payload.get("pushed_total") or ops_payload.get("pushed") or 0)
        pulled = int(ops_payload.get("pulled_total") or ops_payload.get("pulled") or 0)
        self.sync_remote_stats_label.setText(
            f"Remote-Stats: status={status_text} queued={queued} failed={failed} pushed={pushed} pulled={pulled}"
        )
    except Exception:
        self.sync_remote_stats_label.setText("Remote-Stats: nicht verfuegbar")


def _update_sync_schedule_hint(self) -> None:
    if not hasattr(self, "sync_next_run_label"):
        return
    def _set_hint(text: str, color_hex: str) -> None:
        self.sync_next_run_label.setText(text)
        self.sync_next_run_label.setStyleSheet(f"font-size: 12px; color: {color_hex}; font-weight: 600;")

    host = self.window()
    mode = OperatingMode.from_raw(self.sync_mode_combo.currentData() if hasattr(self, "sync_mode_combo") else "local_only")
    interval_seconds = 120
    if hasattr(host, "config"):
        try:
            interval_seconds = max(10, int(host.config.get_sync_interval_seconds()))
        except Exception:
            interval_seconds = 120
    if mode != OperatingMode.HYBRID_SYNC:
        _set_hint("Auto-Sync: pausiert (nur im Hybrid-Sync aktiv)", "#d97706")
        return
    sync_timer = getattr(host, "sync_timer", None)
    if sync_timer is None:
        _set_hint(f"Auto-Sync: Hybrid aktiv (Intervall {interval_seconds}s)", "#dc2626")
        return
    if not sync_timer.isActive():
        _set_hint(f"Auto-Sync: bereit (Intervall {interval_seconds}s, Timer pausiert)", "#d97706")
        return
    remaining_ms = int(sync_timer.remainingTime())
    if remaining_ms < 0:
        _set_hint(f"Auto-Sync: aktiv (Intervall {interval_seconds}s)", "#16a34a")
        return
    remaining_seconds = max(0, int((remaining_ms + 999) / 1000))
    _set_hint(
        f"Auto-Sync: aktiv - naechster Lauf in {remaining_seconds}s (Intervall {interval_seconds}s)",
        "#16a34a",
    )


def _set_sync_state_badge(self, text: str, color_hex: str, hint: str) -> None:
    if hasattr(self, "sync_state_badge"):
        self.sync_state_badge.setText(text)
        self.sync_state_badge.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #ffffff; "
            f"background-color: {color_hex}; border-radius: 10px; padding: 2px 8px;"
        )
    if hasattr(self, "sync_state_hint"):
        self.sync_state_hint.setText(hint)


def retry_sync_conflicts(self) -> None:
    if self._is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Konflikt-Retry ist nur mit Schreibzugriff moeglich.")
        return
    if not hasattr(self.db, "requeue_sync_outbox_conflicts"):
        QtWidgets.QMessageBox.warning(self, "Nicht verfuegbar", "Retry-Funktion ist in diesem Build nicht verfuegbar.")
        return
    try:
        moved = int(self.db.requeue_sync_outbox_conflicts(limit=200))
        self.refresh_sync_status()
        self._toast(f"{moved} Konflikt(e) in Retry verschoben.", "info")
        if moved > 0:
            self.trigger_sync_now()
    except Exception as exc:
        QtWidgets.QMessageBox.critical(self, "Fehler", f"Konflikte konnten nicht in Retry verschoben werden:\n{exc}")


def trigger_sync_now(self) -> None:
    host = self.window()
    if hasattr(host, "_run_sync_cycle"):
        try:
            host._run_sync_cycle()
            self.refresh_sync_status()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Sync", f"Sync-Lauf konnte nicht gestartet werden:\n{exc}")
    else:
        QtWidgets.QMessageBox.information(self, "Sync", "Sync-Service ist in diesem Fenster nicht verfuegbar.")

