"""Dashboard-Widgets (Issue #93)."""
import logging

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)

def create_card_widget():
    """Erstellt ein Card-Widget im Apple-Style"""
    card = QtWidgets.QFrame()
    card.setFrameShape(QtWidgets.QFrame.NoFrame)
    # KEIN setStyleSheet hier!
    return card

class StatusBadge(QtWidgets.QLabel):
    """Interaktives Status-Badge im Apple-Style"""

    clicked = Signal(bool)

    def __init__(self, text, color_key, active=False, parent=None):
        super().__init__(text, parent)
        self.color_key = color_key
        self.is_active = active
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(28)
        self.setMinimumWidth(90)
        self.setFont(AppleTheme.get_font('caption1'))
        self.setProperty("active", active)
        self.update_style()

    def update_style(self):
        c = AppleTheme.current_colors()
        if self.is_active:
            bg = c[f'status_{self.color_key}_bg']
            text_color = c[f'status_{self.color_key}']
            # Brighter text for better contrast on colored bg
            style = f"""
                background-color: {bg};
                color: {text_color};
                border-radius: 14px;
                padding: 2px 10px;
                font-weight: 600;
            """
        else:
            style = f"""
                background-color: {c['status_gray_bg']};
                color: {c['status_gray']};
                border-radius: 14px;
                padding: 2px 10px;
                font-weight: 400;
            """
        self.setStyleSheet(style)

    def mousePressEvent(self, event):
        self.is_active = not self.is_active
        self.setProperty("active", self.is_active)
        self.update_style()
        self.clicked.emit(self.is_active)

class CompletionRing(QtWidgets.QWidget):
    """Kreis-Fortschrittsanzeige für Gesamtstatus"""

    def __init__(self, size=100, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.progress = 0 # 0-100
        self.center_text = "0%"

    def set_progress(self, progress, labels=""):
        self.progress = max(0, min(100, progress))
        self.center_text = f"{int(self.progress)}%"
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        c = AppleTheme.current_colors()
        rect = self.rect().adjusted(5, 5, -5, -5)

        # Hintergrund Ring
        pen = QtGui.QPen(QtGui.QColor(c['status_gray_bg']))
        pen.setWidth(8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Fortschritt Ring
        if self.progress > 0:
            color = c['blue']
            if self.progress >= 100:
                color = c['status_green']

            pen.setColor(QtGui.QColor(color))
            painter.setPen(pen)

            # Start oben (90 Grad)
            span_angle = -self.progress * 3.6
            painter.drawArc(rect, 90 * 16, span_angle * 16)

        # Text in der Mitte
        painter.setPen(QtGui.QColor(c['label']))
        painter.setFont(AppleTheme.get_font('headline'))
        painter.drawText(rect, Qt.AlignCenter, self.center_text)

class TrackingCard(QtWidgets.QFrame):
    """Status-Karte für ein einzelnes Depot"""

    status_changed = Signal(int, int, int) # depot_id, move_status, stock_status

    def __init__(self, depot_id, name, move_status, stock_status, notes="", parent=None):
        super().__init__(parent)
        self.depot_id = depot_id
        self.setObjectName("tracking_card")
        self.setMinimumHeight(100)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Info Bereich
        info_layout = QtWidgets.QVBoxLayout()
        self.name_label = QtWidgets.QLabel(name)
        self.name_label.setFont(AppleTheme.get_font('headline'))
        info_layout.addWidget(self.name_label)

        self.status_label = QtWidgets.QLabel("Status")
        self.status_label.setFont(AppleTheme.get_font('caption1'))
        self.status_label.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']};")
        info_layout.addWidget(self.status_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Badges
        self.badge_moves = StatusBadge("Bewegungen", "blue", move_status == 1)
        self.badge_stock = StatusBadge("Bestand", "green", stock_status == 1)

        self.badge_moves.clicked.connect(self._on_status_changed)
        self.badge_stock.clicked.connect(self._on_status_changed)

        layout.addWidget(self.badge_moves)
        layout.addWidget(self.badge_stock)

        # Notizen Button / Inline field
        self.notes_edit = QtWidgets.QLineEdit(notes)
        self.notes_edit.setPlaceholderText("Notizen...")
        self.notes_edit.setMinimumWidth(120)
        self.notes_edit.setMaximumWidth(220)
        self.notes_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.notes_edit.setFont(AppleTheme.get_font('footnote'))
        self.notes_edit.setStyleSheet("border: none; background: rgba(0,0,0,0.05); padding: 4px 8px; border-radius: 8px;")
        self.notes_edit.editingFinished.connect(self._on_status_changed)
        layout.addWidget(self.notes_edit)

        self._update_card_status()

    def _update_card_status(self):
        m = 1 if self.badge_moves.is_active else 0
        s = 1 if self.badge_stock.is_active else 0

        if m and s:
            self.status_label.setText("Komplett")
            self.status_label.setStyleSheet(f"color: {AppleTheme.current_colors()['status_green']};")
        elif m or s:
            self.status_label.setText("In Arbeit")
            self.status_label.setStyleSheet(f"color: {AppleTheme.current_colors()['blue']};")
        else:
            self.status_label.setText("Offen")
            self.status_label.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']};")

    def _on_status_changed(self):
        self._update_card_status()
        m = 1 if self.badge_moves.is_active else 0
        s = 1 if self.badge_stock.is_active else 0
        self.status_changed.emit(self.depot_id, m, s)

class CollapsibleSection(QtWidgets.QWidget):
    """Aufklappbare Section"""

    toggled = Signal(bool)

    def __init__(self, title="Section", icon_name=None, expanded=True, parent=None):
        super().__init__(parent)
        self.is_expanded = expanded

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, AppleTheme.SPACING['sm'])
        main_layout.setSpacing(0)

        # Header Card
        self.header_card = QtWidgets.QFrame()
        self.header_card.setObjectName("collapsible_header")
        self.header_card.setCursor(Qt.PointingHandCursor)
        self.header_card.setMinimumHeight(56)
        self.header_card.setMaximumHeight(56)

        header_layout = QtWidgets.QHBoxLayout(self.header_card)
        header_layout.setContentsMargins(
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md']
        )

        # Toggle Icon
        self.toggle_icon = QtWidgets.QLabel("▼" if expanded else "▶")
        self.toggle_icon.setFont(AppleTheme.get_font('caption_1'))
        self.toggle_icon.setFixedWidth(20)
        self.toggle_icon.setStyleSheet(f"color: {AppleTheme.current_colors()['blue']};")
        header_layout.addWidget(self.toggle_icon)

        # Section Icon (optional)
        if icon_name:
            self.section_icon = QtWidgets.QLabel()
            self.section_icon.setPixmap(IconManager.get_pixmap(icon_name, color=AppleTheme.current_colors()['blue'], size=20))
            self.section_icon.setFixedWidth(24)
            header_layout.addWidget(self.section_icon)

        # Title
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setFont(AppleTheme.get_font('headline'))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.header_card.mousePressEvent = self._on_header_clicked
        main_layout.addWidget(self.header_card)

        # Content Card
        self.content_card = QtWidgets.QFrame()
        self.content_card.setObjectName("collapsible_content")
        self.content_card.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.content_layout = QtWidgets.QVBoxLayout(self.content_card)
        self.content_layout.setContentsMargins(
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['sm'],
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md']
        )
        self.content_layout.setSpacing(AppleTheme.SPACING['sm'])

        main_layout.addWidget(self.content_card)

        if not expanded:
            self.content_card.setMaximumHeight(0)
            self.content_card.hide()

        # Animation setup
        self.animation = QtCore.QPropertyAnimation(self.content_card, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.animation.finished.connect(self._on_animation_finished)

    def _on_animation_finished(self):
        """Wird aufgerufen wenn Animation fertig ist"""
        if not self.is_expanded:
            self.content_card.hide()
        else:
            # Nach dem Aufklappen Höhenlimit entfernen, damit responsive Inhalte
            # (z. B. umgebrochene Button-Reihen) nicht überlappen.
            self.content_card.setMaximumHeight(16777215)

    def _on_header_clicked(self, event):
        """Toggle Section"""
        self.is_expanded = not self.is_expanded

        # We need an explicit icon here since we replaced emoji emojis.
        # But for text toggle, ▼/▶ is fine.
        _v_icon = IconManager.get_icon("chevron_down", color=AppleTheme.current_colors()['blue'])
        _r_icon = IconManager.get_icon("chevron_right", color=AppleTheme.current_colors()['blue'])
        # if using QLabel we can't set QIcon easily, so let's stick to text for the chevron but clean
        self.toggle_icon.setText("▼" if self.is_expanded else "▶")

        self.animation.stop()
        if self.is_expanded:
            self.content_card.show()
            self.animation.setStartValue(0)
            # Find the actual needed height
            self.animation.setEndValue(self.content_layout.sizeHint().height() + 20)
            self.animation.start()
        else:
            self.animation.setStartValue(self.content_card.height())
            self.animation.setEndValue(0)
            self.animation.start()

        self.toggled.emit(self.is_expanded)

        # Sorge dafür, dass das Parent-Scroll-Area sich anpasst
        if self.parent() and hasattr(self.parent(), 'updateGeometry'):
            self.parent().updateGeometry()

    def add_widget(self, widget):
        """Fügt Widget zum Content hinzu"""
        self.content_layout.addWidget(widget)

