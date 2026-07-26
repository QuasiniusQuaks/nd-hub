"""Hilfsfunktionen für integrierte Dialoge im Hauptfenster."""

from apple_theme import AppleTheme
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

_PATCHED = False
_ORIG_MSG_INFORMATION = QtWidgets.QMessageBox.information
_ORIG_MSG_WARNING = QtWidgets.QMessageBox.warning
_ORIG_MSG_CRITICAL = QtWidgets.QMessageBox.critical
_ORIG_MSG_QUESTION = QtWidgets.QMessageBox.question
_ORIG_INPUT_GET_TEXT = QtWidgets.QInputDialog.getText


def _message_icon_style(icon):
    if icon == QtWidgets.QMessageBox.Critical:
        return "!", "#dc2626", "btn_delete"
    if icon == QtWidgets.QMessageBox.Warning:
        return "!", "#f59e0b", "btn_save"
    if icon == QtWidgets.QMessageBox.Question:
        return "?", "#2563eb", "btn_save"
    return "i", "#2563eb", "btn_save"


def _button_text(std_btn):
    mapping = {
        QtWidgets.QMessageBox.Ok: "OK",
        QtWidgets.QMessageBox.Cancel: "Abbrechen",
        QtWidgets.QMessageBox.Yes: "Ja",
        QtWidgets.QMessageBox.No: "Nein",
    }
    return mapping.get(std_btn, "OK")


def _extract_standard_buttons(buttons):
    ordered = [
        QtWidgets.QMessageBox.Yes,
        QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.Ok,
        QtWidgets.QMessageBox.Cancel,
    ]
    out = [btn for btn in ordered if buttons & btn]
    return out or [QtWidgets.QMessageBox.Ok]


def _resolve_host(parent):
    if parent is None:
        app = QtWidgets.QApplication.instance()
        if app is not None and app.activeWindow() is not None:
            return app.activeWindow()
        return None
    if isinstance(parent, QtWidgets.QMainWindow):
        return parent
    return parent.window() if isinstance(parent, QtWidgets.QWidget) else None


def _embedded_card_stylesheet() -> str:
    """Farben aus AppleTheme — passt sich Light/Dark an (Kontext-Dialoge, Formulare)."""
    c = AppleTheme.current_colors()
    bg = c["bg_secondary"]
    lbl = c["label"]
    _sec = c["secondary_label"]
    sep = c["separator"]
    inp = c["bg_tertiary"]
    return (
        "QWidget#embedded_dialog_card {"
        f"background-color: {bg};"
        "border-radius: 12px;"
        "}"
        "QWidget#embedded_dialog_card QLabel {"
        f"color: {lbl};"
        "background: transparent;"
        "border: none;"
        "padding: 0;"
        "}"
        f"QWidget#embedded_dialog_card QCheckBox {{ color: {lbl}; background: transparent; }}"
        f"QWidget#embedded_dialog_card QGroupBox {{ color: {lbl}; font-weight: 600; }}"
        "QWidget#embedded_dialog_card QGroupBox::title {"
        f"color: {lbl}; subcontrol-origin: margin; left: 8px; padding: 0 4px;"
        "}"
        "QWidget#embedded_dialog_card QLineEdit, QWidget#embedded_dialog_card QTextEdit, "
        "QWidget#embedded_dialog_card QPlainTextEdit, QWidget#embedded_dialog_card QComboBox, "
        "QWidget#embedded_dialog_card QSpinBox, QWidget#embedded_dialog_card QDateEdit {"
        "min-height: 38px;"
        f"border: 1px solid {sep};"
        "border-radius: 8px;"
        "padding: 6px 10px;"
        f"background: {inp};"
        f"color: {lbl};"
        "}"
        "QWidget#embedded_dialog_card QPushButton { min-height: 38px; }"
    )


def exec_embedded_dialog(parent: QtWidgets.QWidget, dialog: QtWidgets.QDialog) -> int:
    """Zeigt einen QDialog als eingebettetes Overlay statt als separates Fenster."""
    host = _resolve_host(parent)
    if host is None:
        return dialog.exec()

    # Sehr große Dialoge (z.B. Setup-Wizard ~92% Fläche) als natives Fenster:
    # nested QEventLoop + setParent(Widget) + setFixedSize hat unter Windows
    # native Segfaults (Exit 139) nach Login ausgelöst.
    fill_ratio_pre = dialog.property("embedded_fill_ratio")
    if isinstance(fill_ratio_pre, (float, int)) and float(fill_ratio_pre) >= 0.8:
        dialog.setParent(host)
        dialog.setWindowFlag(Qt.Window, True)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setModal(True)
        return dialog.exec()

    overlay = QtWidgets.QWidget(host)
    overlay.setObjectName("embedded_dialog_overlay")
    dim = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 170)"
    overlay.setStyleSheet(
        f"QWidget#embedded_dialog_overlay {{ background-color: {dim}; }}"
    )
    overlay.setGeometry(host.rect())

    layout = QtWidgets.QVBoxLayout(overlay)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.addStretch()

    # Dialog in Widget-Modus überführen und im Overlay anzeigen.
    dialog.setObjectName("embedded_dialog_card")
    dialog.setParent(overlay)
    dialog.setWindowFlags(Qt.Widget)
    dialog.setModal(False)
    dialog.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
    dialog.setMinimumWidth(460)
    dialog.setStyleSheet(_embedded_card_stylesheet())
    fill_ratio = dialog.property("embedded_fill_ratio")
    aspect_ratio = str(dialog.property("embedded_aspect_ratio") or "").strip()
    if isinstance(fill_ratio, (float, int)):
        ratio = min(max(float(fill_ratio), 0.1), 1.0)
        margin_l, margin_t, margin_r, margin_b = layout.getContentsMargins()
        avail_w = max(1, overlay.width() - margin_l - margin_r)
        avail_h = max(1, overlay.height() - margin_t - margin_b)
        max_w = max(1, int(avail_w * ratio))
        max_h = max(1, int(avail_h * ratio))
        target_w, target_h = max_w, max_h
        if aspect_ratio == "16:9":
            target_w = max_w
            target_h = int(target_w * 9 / 16)
            if target_h > max_h:
                target_h = max_h
                target_w = int(target_h * 16 / 9)
        target_w = max(dialog.minimumWidth(), min(target_w, avail_w))
        target_h = max(dialog.minimumHeight(), min(target_h, avail_h))
        dialog.setFixedSize(target_w, target_h)
    else:
        dialog.adjustSize()
    layout.addWidget(dialog, alignment=Qt.AlignHCenter)
    layout.addStretch()

    result = QtWidgets.QDialog.Rejected
    loop = QtCore.QEventLoop()

    def _finish(code):
        nonlocal result
        result = code
        loop.quit()

    dialog.finished.connect(_finish)
    overlay.show()
    overlay.raise_()
    dialog.show()
    loop.exec()
    # WICHTIG: Dialog vom Overlay lösen, BEVOR das Overlay gelöscht wird.
    # Sonst stirbt der Dialog mit (Qt C++ delete) und Aufrufer, die danach
    # z.B. dialog.get_passwords() lesen, triggern einen nativen Segfault
    # (Exit 139) — Python-Exception-Handler greift nicht.
    try:
        dialog.finished.disconnect(_finish)
    except (RuntimeError, TypeError):
        pass
    dialog.hide()
    dialog.setParent(None)
    overlay.hide()
    overlay.deleteLater()
    # Events verarbeiten, damit deleteLater das Overlay wirklich freigibt,
    # ohne den (jetzt entkoppelten) Dialog mitzunehmen.
    QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
    return result


def get_text_embedded(
    parent: QtWidgets.QWidget,
    title: str,
    label: str,
    mode: QtWidgets.QLineEdit.EchoMode = QtWidgets.QLineEdit.Normal,
    text: str = "",
):
    """Ersatz für QInputDialog.getText mit eingebetteter Darstellung."""
    dialog = QtWidgets.QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextEchoMode(mode)
    dialog.setTextValue(text)
    button_box = dialog.findChild(QtWidgets.QDialogButtonBox)
    if button_box is not None:
        ok_btn = button_box.button(QtWidgets.QDialogButtonBox.Ok)
        cancel_btn = button_box.button(QtWidgets.QDialogButtonBox.Cancel)
        if ok_btn is not None:
            ok_btn.setObjectName("btn_save")
            ok_btn.setMinimumHeight(40)
        if cancel_btn is not None:
            cancel_btn.setObjectName("btn_secondary")
            cancel_btn.setMinimumHeight(40)
    result = exec_embedded_dialog(parent, dialog)
    return dialog.textValue(), result == QtWidgets.QDialog.Accepted


def _show_message_embedded(parent, icon, title, text, buttons, default_button):
    host = _resolve_host(parent)
    if host is None:
        return None
    dialog = QtWidgets.QDialog(host)
    dialog.setWindowTitle(title)
    dialog._clicked_button = QtWidgets.QMessageBox.NoButton

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(14)

    glyph, color, primary_style = _message_icon_style(icon)
    header_row = QtWidgets.QHBoxLayout()
    icon_label = QtWidgets.QLabel(glyph)
    icon_label.setAlignment(Qt.AlignCenter)
    icon_label.setFixedSize(30, 30)
    icon_label.setStyleSheet(
        f"background-color: {color}; color: white; border-radius: 15px; font-size: 16px; font-weight: 700;"
    )
    header_row.addWidget(icon_label)

    tc = AppleTheme.current_colors()
    title_label = QtWidgets.QLabel(title)
    title_label.setStyleSheet(
        f"font-size: 20px; font-weight: 700; color: {tc['label']}; background: transparent;"
    )
    header_row.addWidget(title_label)
    header_row.addStretch()
    layout.addLayout(header_row)

    msg_label = QtWidgets.QLabel(text)
    msg_label.setWordWrap(True)
    msg_label.setStyleSheet(
        f"font-size: 14px; color: {tc['secondary_label']}; background: transparent;"
    )
    layout.addWidget(msg_label)

    button_row = QtWidgets.QHBoxLayout()
    button_row.addStretch()
    all_buttons = _extract_standard_buttons(buttons)
    for std_btn in all_buttons:
        btn = QtWidgets.QPushButton(_button_text(std_btn))
        btn.setMinimumHeight(40)
        if std_btn in (QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.No):
            btn.setObjectName("btn_secondary")
        else:
            btn.setObjectName(primary_style)
        if default_button and std_btn == default_button:
            btn.setDefault(True)
            btn.setAutoDefault(True)

        def _on_click(_, code=std_btn):
            dialog._clicked_button = code
            dialog.accept()

        btn.clicked.connect(_on_click)
        button_row.addWidget(btn)
    layout.addLayout(button_row)

    exec_embedded_dialog(host, dialog)
    return dialog._clicked_button


def install_embedded_dialog_patches():
    """Patcht QMessageBox/QInputDialog statische Methoden für integrierte Darstellung."""
    global _PATCHED
    if _PATCHED:
        return

    def _information(parent, title, text, buttons=QtWidgets.QMessageBox.Ok, defaultButton=QtWidgets.QMessageBox.NoButton):
        result = _show_message_embedded(
            parent, QtWidgets.QMessageBox.Information, title, text, buttons, defaultButton
        )
        if result is None:
            return _ORIG_MSG_INFORMATION(parent, title, text, buttons, defaultButton)
        return result

    def _warning(parent, title, text, buttons=QtWidgets.QMessageBox.Ok, defaultButton=QtWidgets.QMessageBox.NoButton):
        result = _show_message_embedded(
            parent, QtWidgets.QMessageBox.Warning, title, text, buttons, defaultButton
        )
        if result is None:
            return _ORIG_MSG_WARNING(parent, title, text, buttons, defaultButton)
        return result

    def _critical(parent, title, text, buttons=QtWidgets.QMessageBox.Ok, defaultButton=QtWidgets.QMessageBox.NoButton):
        result = _show_message_embedded(
            parent, QtWidgets.QMessageBox.Critical, title, text, buttons, defaultButton
        )
        if result is None:
            return _ORIG_MSG_CRITICAL(parent, title, text, buttons, defaultButton)
        return result

    def _question(parent, title, text, buttons=QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, defaultButton=QtWidgets.QMessageBox.NoButton):
        result = _show_message_embedded(
            parent, QtWidgets.QMessageBox.Question, title, text, buttons, defaultButton
        )
        if result is None:
            return _ORIG_MSG_QUESTION(parent, title, text, buttons, defaultButton)
        return result

    def _get_text(parent, title, label, mode=QtWidgets.QLineEdit.Normal, text="", flags=QtCore.Qt.WindowFlags(), inputMethodHints=QtCore.Qt.ImhNone):
        host = _resolve_host(parent)
        if host is None:
            return _ORIG_INPUT_GET_TEXT(parent, title, label, mode, text, flags, inputMethodHints)
        return get_text_embedded(host, title, label, mode, text)

    QtWidgets.QMessageBox.information = staticmethod(_information)
    QtWidgets.QMessageBox.warning = staticmethod(_warning)
    QtWidgets.QMessageBox.critical = staticmethod(_critical)
    QtWidgets.QMessageBox.question = staticmethod(_question)
    QtWidgets.QInputDialog.getText = staticmethod(_get_text)
    _PATCHED = True

