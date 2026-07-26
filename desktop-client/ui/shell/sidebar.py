"""MainWindow shell helpers (Issue #93)."""
from __future__ import annotations

import logging
import os

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from ui.resources import LOGO_BASE64
from ui.shell.constants import PageIndex

logger = logging.getLogger("ND-Hub")

def _create_sidebar(self) -> QtWidgets.QFrame:
    """Erstellt Sidebar mit Navigation"""
    sidebar = QtWidgets.QFrame()
    sidebar.setObjectName("sidebar")
    self.sidebar = sidebar
    sidebar.setMinimumWidth(230)
    sidebar.setMaximumWidth(260)
    sidebar.setSizePolicy(
        QtWidgets.QSizePolicy.Fixed,
        QtWidgets.QSizePolicy.Expanding
    )

    layout = QtWidgets.QVBoxLayout(sidebar)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    content_layout = QtWidgets.QVBoxLayout()
    content_layout.setContentsMargins(0, 16, 0, 16)
    content_layout.setSpacing(0)

    # Logo-Bereich
    content_layout.addWidget(self._create_logo_container())
    content_layout.addSpacing(20)

    # Navigation
    self.sidebar_buttons = []
    self._add_navigation_buttons(content_layout)

    # User-Bereich
    content_layout.addStretch()
    self._add_user_section(content_layout)
    layout.addLayout(content_layout)

    return sidebar


def _update_sidebar_width(self, window_width: int) -> None:
    """Hält Sidebar stabil, aber auf kleinen Fenstern kompakt."""
    if not hasattr(self, "sidebar"):
        return
    target = 230 if window_width < 1300 else 250
    self.sidebar.setMinimumWidth(target)
    self.sidebar.setMaximumWidth(target)


def _create_logo_container(self) -> QtWidgets.QWidget:
    """Erstellt Logo-Container (wiederverwendbar)"""
    container = QtWidgets.QWidget()
    container.setObjectName("logo_container")
    container.setStyleSheet("""
        QWidget#logo_container {
            background: transparent;
            border: none;
            margin: 0 12px 16px 12px;
        }
    """)

    layout = QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    # Logo laden
    logo_label = self._create_logo_label()
    layout.addWidget(logo_label)

    # # Titel
    # title = QtWidgets.QLabel("Verwaltung ND-Hubs")
    # title.setFont(AppleTheme.get_font('title_3'))
    # title.setStyleSheet(f"color: {AppleTheme.COLORS['label']}; font-weight: 700; background: transparent;")
    # title.setAlignment(Qt.AlignCenter)
    # layout.addWidget(title)

    return container


def _create_logo_label(self) -> QtWidgets.QWidget:
    """
    Erstellt Logo-Label mit abgerundeten Ecken und Beschriftung
    Base64 oder Emoji-Fallback
    """
    # Container für Logo + Text
    container = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)  # Abstand zwischen Logo und Text

    try:
        import base64

        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPainterPath

        logo_data = base64.b64decode(LOGO_BASE64)
        pixmap = QtGui.QPixmap()

        if pixmap.loadFromData(logo_data) and not pixmap.isNull():
            # Logo skalieren
            scaled_pixmap = pixmap.scaled(
                84, 84,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Erstelle ein neues Pixmap mit transparentem Hintergrund
            size = scaled_pixmap.size()
            rounded_pixmap = QtGui.QPixmap(size)
            rounded_pixmap.fill(Qt.transparent)

            # Male das Logo mit abgerundeten Ecken
            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Erstelle Pfad mit abgerundeten Ecken
            path = QPainterPath()
            rect = QRectF(0, 0, size.width(), size.height())
            radius = 16  # Radius anpassbar (8-20 empfohlen)
            path.addRoundedRect(rect, radius, radius)

            # Clipping anwenden und Logo zeichnen
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled_pixmap)
            painter.end()

            # Logo-Label
            logo_label = QtWidgets.QLabel()
            logo_label.setPixmap(rounded_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("QLabel { background: transparent; }")
            layout.addWidget(logo_label)

    except Exception as e:
        logger.debug(f"Logo-Fehler: {e}. Fallback auf Emoji.")

        # Fallback: Emoji
        logo_label = QtWidgets.QLabel("")
        logo_label.setFont(AppleTheme.get_font('largetitle'))
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("QLabel { background: transparent; }")
        layout.addWidget(logo_label)

    # ===== BRANDING UNTER DEM LOGO =====
    brand_label = QtWidgets.QLabel("ND-Hub")
    brand_label.setFont(AppleTheme.get_font('headline'))
    brand_label.setAlignment(Qt.AlignCenter)
    brand_label.setStyleSheet("""
        QLabel {
            color: #ecf0f1;
            background: transparent;
            font-weight: 800;
            padding-top: 4px;
        }
    """)
    layout.addWidget(brand_label)

    claim_label = QtWidgets.QLabel("Die Notfalldepot-Verwaltung")
    claim_label.setFont(AppleTheme.get_font('caption1'))
    claim_label.setWordWrap(True)
    claim_label.setAlignment(Qt.AlignCenter)
    claim_label.setMaximumWidth(170)
    claim_label.setStyleSheet("""
        QLabel {
            color: #bdc3c7;
            background: transparent;
            font-weight: 500;
            padding-bottom: 4px;
        }
    """)
    layout.addWidget(claim_label)
    # ===== ENDE BRANDING =====

    return container


def _add_navigation_buttons(self, layout: QtWidgets.QVBoxLayout) -> None:
    """Fügt Navigations-Buttons zur Sidebar hinzu"""
    buttons = [
        ("Dashboard", PageIndex.DASHBOARD, "home"),
        ("Bewegungen", PageIndex.MOVEMENTS, "activity"),
        ("Verlauf", PageIndex.HISTORIE, "clock"),
        ("Auswertungen", PageIndex.AUSWERTUNGEN, "pie_chart"),
        ("Import", PageIndex.IMPORT, "download"),
        ("E-Mail", PageIndex.EMAIL, "mail"),
        ("Grundeinstellungen", PageIndex.GRUNDEINSTELLUNGEN, "settings"),
    ]

    for text, _page_idx, icon_name in buttons:
        btn = self.create_sidebar_button(text, icon_name)
        layout.addWidget(btn)


def _add_user_section(self, layout: QtWidgets.QVBoxLayout) -> None:
    """Fügt User-Info und -Buttons zur Sidebar hinzu"""
    # Trennlinie
    separator = QtWidgets.QFrame()
    separator.setFrameShape(QtWidgets.QFrame.HLine)
    separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin: 10px 16px;")
    layout.addWidget(separator)

    # User-Info-Widget
    user_widget = self._create_user_info_widget()
    layout.addWidget(user_widget)

    # Profilbild für den aktuellen Benutzer
    self.btn_change_avatar = self._create_styled_button("Profilbild ändern", self.change_user_avatar)
    self.btn_change_avatar.setIcon(IconManager.get_icon("folder", color="#ecf0f1"))
    layout.addWidget(self.btn_change_avatar)

    self.btn_remove_avatar = self._create_styled_button("Profilbild entfernen", self.remove_user_avatar)
    self.btn_remove_avatar.setIcon(IconManager.get_icon("x", color="#ecf0f1"))
    layout.addWidget(self.btn_remove_avatar)

    # Passwort-Button
    self.btn_change_password = self._create_styled_button("Passwort ändern", self.change_user_password)
    self.btn_change_password.setIcon(IconManager.get_icon("key", color="#ecf0f1"))
    layout.addWidget(self.btn_change_password)

    # Theme-Toggle
    text = " Dark Mode" if not AppleTheme.is_dark_mode else " Light Mode"
    icon_name = "moon" if not AppleTheme.is_dark_mode else "sun"
    self.btn_theme_toggle = self._create_styled_button(text, self.toggle_theme)
    self.btn_theme_toggle.setIcon(IconManager.get_icon(icon_name, color="#ecf0f1"))
    layout.addWidget(self.btn_theme_toggle)

    # Logout
    self.btn_logout = self._create_logout_button()
    layout.addWidget(self.btn_logout)


def _apply_chrome_overlay_styles(self) -> None:
    """Banner, Busy- und Login-Overlays an AppleTheme anpassen (Dark/Light)."""
    c = AppleTheme.current_colors()
    dim = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 170)"
    dim_busy = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 110)"

    if hasattr(self, "read_only_banner"):
        self.read_only_banner.setStyleSheet(
            f"background-color: {c['status_orange_bg']}; border-bottom: 1px solid {c['status_orange']};"
        )
    if hasattr(self, "read_only_banner_label"):
        self.read_only_banner_label.setStyleSheet(
            f"color: {c['status_orange']}; font-size: 12px; font-weight: 600;"
        )

    if hasattr(self, "busy_overlay"):
        self.busy_overlay.setStyleSheet(
            f"QWidget#page_busy_overlay {{ background-color: {dim_busy}; }}"
        )
    if hasattr(self, "_busy_card_frame"):
        self._busy_card_frame.setStyleSheet(
            f"QFrame#busy_card {{"
            f"background-color: {c['bg_secondary']};"
            f"border: 1px solid {c['separator']};"
            f"border-radius: 12px;"
            f"padding: 18px;"
            f"}}"
        )
    if hasattr(self, "busy_label"):
        self.busy_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {c['label']}; background: transparent;"
        )
    if hasattr(self, "busy_hint_label"):
        self.busy_hint_label.setStyleSheet(
            f"font-size: 12px; color: {c['secondary_label']}; background: transparent;"
        )

    if hasattr(self, "login_overlay"):
        self.login_overlay.setStyleSheet(
            f"QWidget#login_overlay {{ background-color: {dim}; }}"
        )
    if hasattr(self, "_login_card_frame"):
        self._login_card_frame.setStyleSheet(
            f"QFrame#login_card {{"
            f"background-color: {c['bg_secondary']};"
            f"border: 1px solid {c['separator']};"
            f"border-radius: 12px;"
            f"padding: 28px;"
            f"}}"
        )
    if hasattr(self, "_login_title_label"):
        self._login_title_label.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {c['label']}; background: transparent;"
        )
    if hasattr(self, "_login_subtitle_label"):
        self._login_subtitle_label.setStyleSheet(
            f"font-size: 14px; color: {c['secondary_label']}; line-height: 1.4; background: transparent;"
        )
    if hasattr(self, "_login_hint_label"):
        self._login_hint_label.setStyleSheet(
            f"font-size: 12px; color: {c['tertiary_label']}; background: transparent;"
        )
    le_style = (
        f"QLineEdit {{"
        f"background-color: {c['bg_tertiary']};"
        f"color: {c['label']};"
        f"border: 1px solid {c['separator']};"
        f"border-radius: 8px;"
        f"padding: 8px 10px;"
        f"selection-background-color: {c['blue']};"
        f"selection-color: #ffffff;"
        f"}}"
    )
    if hasattr(self, "login_user_input"):
        self.login_user_input.setStyleSheet(le_style)
    if hasattr(self, "login_password_input"):
        self.login_password_input.setStyleSheet(le_style)
    if hasattr(self, "login_error_label"):
        self.login_error_label.setStyleSheet(
            f"color: {c['red']}; font-size: 12px; background: transparent;"
        )


def toggle_theme(self) -> None:
    """Schaltet zwischen Light- und Dark-Mode um"""
    AppleTheme.is_dark_mode = not AppleTheme.is_dark_mode

    # UI aktualisieren
    self.setStyleSheet(AppleTheme.get_stylesheet())
    self._apply_chrome_overlay_styles()

    # Toggle-Button Text aktualisieren
    text = " Dark Mode" if not AppleTheme.is_dark_mode else " Light Mode"
    icon_name = "moon" if not AppleTheme.is_dark_mode else "sun"
    self.btn_theme_toggle.setText(text)
    self.btn_theme_toggle.setIcon(IconManager.get_icon(icon_name, color="#ecf0f1"))

    # Sidebar-Buttons aktualisieren (Farben neu laden)
    for btn in self.sidebar_buttons:
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    # Aktiven Button neu markieren
    self.set_active_button(self.stack.currentIndex())

    # Aktuelle Seite benachrichtigen (speziell für Matplotlib/Charts)
    current_page = self.stack.currentWidget()
    if hasattr(current_page, "refresh_theme"):
        current_page.refresh_theme()

    logging.info(f"Theme gewechselt: {'Dark' if AppleTheme.is_dark_mode else 'Light'} Mode")


def _create_user_info_widget(self) -> QtWidgets.QWidget:
    """Erstellt User-Info-Widget (Icon, Name, Rolle)"""
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    layout.setContentsMargins(16, 8, 16, 8)
    layout.setSpacing(4)

    # Icon
    self.user_avatar_label = QtWidgets.QLabel()
    self.user_avatar_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(self.user_avatar_label)

    # Name
    self.user_name_label = QtWidgets.QLabel(self.security.get_current_user() or "Nicht angemeldet")
    c = AppleTheme.current_colors()
    self.user_name_label.setStyleSheet(f"color: {c['sidebar_text_active']}; font-size: 13px; font-weight: 600;")
    self.user_name_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(self.user_name_label)

    # Rolle
    self.user_role_label = QtWidgets.QLabel(f"({self.security.get_current_role() or '-'})")
    self.user_role_label.setStyleSheet(f"color: {c['sidebar_text']}; font-size: 11px;")
    self.user_role_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(self.user_role_label)

    self.user_mode_label = QtWidgets.QLabel("")
    self.user_mode_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(self.user_mode_label)
    self._refresh_user_sidebar_state()

    return widget


def _refresh_user_sidebar_state(self) -> None:
    """Synchronisiert Benutzerinfos und Admin-Buttons nach Login."""
    if hasattr(self, "user_name_label"):
        self.user_name_label.setText(self.security.get_current_user() or "Nicht angemeldet")
    if hasattr(self, "user_role_label"):
        self.user_role_label.setText(f"({self.security.get_current_role() or '-'})")
    current_user = self.security.get_current_user() if hasattr(self, "security") else None
    if hasattr(self, "user_mode_label"):
        if not current_user:
            self.user_mode_label.setText("")
            if hasattr(self, "read_only_banner"):
                self.read_only_banner.setVisible(False)
        elif hasattr(self, "db") and self.db.is_read_only_mode():
            self.user_mode_label.setText("Modus: Nur Lesen")
            oc = AppleTheme.current_colors()
            self.user_mode_label.setStyleSheet(
                f"color: {oc['status_orange']}; font-size: 11px; font-weight: 600;"
            )
            if hasattr(self, "read_only_banner"):
                self.read_only_banner.setVisible(True)
        else:
            self.user_mode_label.setText("Modus: Schreiben")
            oc = AppleTheme.current_colors()
            self.user_mode_label.setStyleSheet(
                f"color: {oc['status_green']}; font-size: 11px; font-weight: 600;"
            )
            if hasattr(self, "read_only_banner"):
                self.read_only_banner.setVisible(False)
    self._update_user_avatar_display()


def _apply_write_mode_to_page(self, page: QtWidgets.QWidget) -> None:
    """Deaktiviert Schreib-Buttons bei read-only Sessions."""
    if page is None or not hasattr(self, "db"):
        return
    read_only = self.db.is_read_only_mode()
    for widget in page.findChildren(QtWidgets.QAbstractButton):
        object_name = widget.objectName() or ""
        requires_write = bool(widget.property("requires_write"))
        btn_class = str(widget.property("class") or "")
        if object_name in {"btn_add", "btn_save", "btn_delete"} or btn_class in {"btn_add", "btn_save", "btn_delete"} or requires_write:
            widget.setEnabled(not read_only)


def _update_user_avatar_display(self) -> None:
    """Aktualisiert Profilbild in der Sidebar."""
    if not hasattr(self, "user_avatar_label"):
        return
    avatar_path = self.security.get_current_user_avatar_path()
    if avatar_path and os.path.exists(avatar_path):
        pixmap = QtGui.QPixmap(avatar_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(44, 44, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            rounded = QtGui.QPixmap(44, 44)
            rounded.fill(Qt.transparent)
            painter = QtGui.QPainter(rounded)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, 44, 44)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            self.user_avatar_label.setPixmap(rounded)
            return
    self.user_avatar_label.setPixmap(IconManager.get_pixmap("user", color="#ecf0f1", size=36))


def _create_styled_button(self, text: str, callback) -> QtWidgets.QPushButton:
    """Factory für Sidebar-Buttons (DRY)"""
    btn = QtWidgets.QPushButton(text)
    btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #bdc3c7;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            padding: 8px 12px;
            text-align: center;
            margin: 4px 16px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: rgba(52, 152, 219, 0.2);
            color: #ecf0f1;
        }
    """)
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(callback)
    return btn


def _create_logout_button(self) -> QtWidgets.QPushButton:
    """Erstellt Logout-Button (spezielles Styling)"""
    btn = QtWidgets.QPushButton(" Abmelden")
    btn.setIcon(IconManager.get_icon("log_out", color="white"))
    btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(231, 76, 60, 0.8);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 12px;
            text-align: center;
            margin: 8px 16px 16px 16px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: rgba(192, 57, 43, 1);
        }
    """)
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(self.logout)
    return btn


def create_sidebar_button(self, text: str, icon_name: str = None) -> QtWidgets.QPushButton:
    """Erstellt Sidebar-Button mit Auto-Registrierung und Icon"""
    btn = QtWidgets.QPushButton(f" {text}")
    if icon_name:
        btn.setIcon(IconManager.get_icon(icon_name, color="#ecf0f1"))
        btn.setIconSize(QtCore.QSize(18, 18))
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(lambda: self.on_sidebar_click(btn))
    self.sidebar_buttons.append(btn)
    return btn


def on_sidebar_click(self, clicked_btn: QtWidgets.QPushButton) -> None:
    """Handler für Sidebar-Navigation"""
    idx = self.sidebar_buttons.index(clicked_btn)
    self.switch_to_page(idx)


def set_active_button(self, active_idx: int) -> None:
    """Markiert aktiven Sidebar-Button"""
    for i, btn in enumerate(self.sidebar_buttons):
        btn.setProperty("active", "true" if i == active_idx else "false")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

