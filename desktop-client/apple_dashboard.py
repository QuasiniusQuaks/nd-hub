"""
Apple-Style Dashboard für ND-Hub
"""

import logging
from datetime import datetime

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal
from responsive_widgets import FlowLayout, ResponsiveWidget
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog
from ui.dialogs.verfall_detail_dialog import VerfallDetailDialog
from verfall_widget import VerfallWidget

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

class AppleDashboard(ResponsiveWidget):
    """Apple-Style Dashboard mit responsivem Layout"""

    requestedPage = Signal(int)

    def _apply_layout_mode(self, mode):
        """Passt das Dashboard an die Bildschirmgröße an"""
        if not hasattr(self, 'sections_layout'):
            return

        _c = AppleTheme.current_colors()

        if mode in ['mobile', 'compact']:
            # Kompakter Modus für kleine Bildschirme
            self.sections_layout.setSpacing(AppleTheme.SPACING['sm'])
            self.sections_layout.setContentsMargins(
                AppleTheme.SPACING['md'],
                AppleTheme.SPACING['md'],
                AppleTheme.SPACING['md'],
                AppleTheme.SPACING['md']
            )
            if hasattr(self, 'date_label'):
                self.date_label.hide() # Platz sparen am Handy
            if hasattr(self, 'quick_access_title'):
                self.quick_access_title.setVisible(mode != 'mobile')
            if hasattr(self, 'completion_ring'):
                self.completion_ring.setFixedSize(96, 96)
            if hasattr(self, 'tracking_scroll'):
                self.tracking_scroll.setMinimumHeight(200)
            if hasattr(self, 'quick_access_btns'):
                for btn in self.quick_access_btns:
                    btn.setMinimumWidth(150)
        else:
            # Normaler Modus
            self.sections_layout.setSpacing(AppleTheme.SPACING['md'])
            self.sections_layout.setContentsMargins(
                AppleTheme.SPACING['lg'],
                AppleTheme.SPACING['lg'],
                AppleTheme.SPACING['lg'],
                AppleTheme.SPACING['lg']
            )
            if hasattr(self, 'date_label'):
                self.date_label.show()
            if hasattr(self, 'quick_access_title'):
                self.quick_access_title.setVisible(True)
            if hasattr(self, 'completion_ring'):
                self.completion_ring.setFixedSize(120, 120)
            if hasattr(self, 'tracking_scroll'):
                self.tracking_scroll.setMinimumHeight(240)
            if hasattr(self, 'quick_access_btns'):
                for btn in self.quick_access_btns:
                    btn.setMinimumWidth(180)

        # Refresh KPI Grid falls vorhanden
        if hasattr(self, 'kpi_container_layout'):
            if mode in ['mobile', 'compact']:
                self.kpi_container_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
            else:
                self.kpi_container_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)

        # Refresh Overview Row 2 falls vorhanden
        if hasattr(self, 'overview_row2_layout'):
            if mode in ['mobile', 'compact']:
                self.overview_row2_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
            else:
                self.overview_row2_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)

        # Sicherstellen, dass geöffnete Sections nach Layoutwechsel nicht clippen.
        if hasattr(self, 'sections'):
            for section in self.sections.values():
                if getattr(section, 'is_expanded', False):
                    section.content_card.setMaximumHeight(16777215)
                    section.updateGeometry()

    def refresh_theme(self):
        """Aktualisiert das Design des Dashboards bei Theme-Wechsel"""
        # Header aktualisieren (Datums-Label etc.)
        _c = AppleTheme.current_colors()
        if hasattr(self, 'date_label'):
            self.date_label.style().unpolish(self.date_label)
            self.date_label.style().polish(self.date_label)

        # Sektionen aktualisieren
        for section in self.sections.values():
            section.style().unpolish(section)
            section.style().polish(section)

            # Falls die Sektion ein Verfall-Widget hat
            if hasattr(self, 'verfall_widget'):
                if hasattr(self.verfall_widget, 'refresh_theme'):
                    self.verfall_widget.refresh_theme()
                else:
                    self.verfall_widget.update()

        # Quick Actions aktualisieren
        self._update_quick_actions_style()

        # Tracking Cards aktualisieren
        if hasattr(self, 'tracking_cards_layout'):
            for i in range(self.tracking_cards_layout.count()):
                item = self.tracking_cards_layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if hasattr(w, 'badge_moves'):
                        w.badge_moves.update_style()
                    if hasattr(w, 'badge_stock'):
                        w.badge_stock.update_style()
                    w.update()

        # Ganzes Widget neu zeichnen
        self.update()

    def _update_quick_actions_style(self):
        """Aktualisiert das Styling der Schnellzugriff-Buttons basierend auf dem aktuellen Theme"""
        if not hasattr(self, 'quick_access_btns'):
            return

        c = AppleTheme.current_colors()

        # Container-Background
        if hasattr(self, 'quick_access_container'):
            self.quick_access_container.setStyleSheet(f"background-color: {c['bg_tertiary']}; border-radius: 16px;")

        # Title-Label
        if hasattr(self, 'quick_access_title'):
            self.quick_access_title.setStyleSheet(f"color: {c['secondary_label']}; letter-spacing: 1.2px; font-weight: 700;")

        # Buttons
        for btn in self.quick_access_btns:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['blue']};
                    color: white;
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {c['green']};
                    margin-top: -2px;
                    margin-bottom: 2px;
                }}
                QPushButton:pressed {{
                    background-color: {c['green']}dd;
                    margin-top: 1px;
                    margin-bottom: -1px;
                }}
            """)

    def __init__(self, db, verfallmanager=None, parent=None):
        self.db = db
        self.verfallmanager = verfallmanager  # HIER setzen, VOR setupui()
        super().__init__(parent)
        self._setup_ui()

        # Daten laden
        self.refresh_tracking()
        self.refresh_activities()

    def _setup_ui(self):
        """UI initialisieren"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # Container
        self.container = QtWidgets.QWidget()
        self.container.setObjectName("dashboard_container")

        # Vertikales Layout für Sections
        self.sections_layout = QtWidgets.QVBoxLayout(self.container)
        self.sections_layout.setSpacing(AppleTheme.SPACING['md'])
        self.sections_layout.setContentsMargins(
            AppleTheme.SPACING['lg'],
            AppleTheme.SPACING['lg'],
            AppleTheme.SPACING['lg'],
            AppleTheme.SPACING['lg']
        )

        # Header erstellen
        self._create_header()

        # Cards erstellen
        self._create_cards()

        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

    def _create_header(self):
        """Erstellt den Dashboard-Header ohne Border, größerer Titel"""
        self.header_widget = QtWidgets.QWidget()
        self.header_widget.setObjectName("dashboard_header")

        header_layout = QtWidgets.QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, AppleTheme.SPACING['md'])

        # Titel - OHNE Emoji, GRÖßER
        title = QtWidgets.QLabel("Dashboard")
        title.setFont(AppleTheme.get_font('largetitle'))
        title.setObjectName("dashboard_title")

        header_layout.addWidget(title)

        header_layout.addStretch()

        # Datum & Version - OHNE Border
        from nd_hub import VERSION
        header_text = f"V{VERSION}  •  {datetime.now().strftime('%d. %B %Y, %H:%M Uhr')}"
        self.date_label = QtWidgets.QLabel(header_text)
        self.date_label.setFont(AppleTheme.get_font('subheadline'))
        self.date_label.setObjectName("dashboard_date")

        header_layout.addWidget(self.date_label)

        # Header zu Grid hinzufügen (spanning alle Spalten)
        self.sections_layout.addWidget(self.header_widget)

    def _create_cards(self):
        """Erstellt Collapsible Sections"""
        self.sections = {}

        # 1. Konsolidierte Übersicht
        overview_section = CollapsibleSection("Übersicht", icon_name="info", expanded=True)
        overview_content = self._create_overview_content()
        overview_section.add_widget(overview_content)
        self.sections['overview'] = overview_section
        self.sections_layout.addWidget(overview_section)

        # 2. Verfall Section
        verfall_section = CollapsibleSection("Verfallswarnungen", icon_name="alert", expanded=False)
        verfall_content = self._create_verfall_section()
        verfall_section.add_widget(verfall_content)
        self.sections['verfall'] = verfall_section
        self.sections_layout.addWidget(verfall_section)

        # 3. Aktivitäten Section
        activity_section = CollapsibleSection("Letzte Aktivitäten", icon_name="activity", expanded=False)
        activity_content = self._create_activities_section()
        activity_section.add_widget(activity_content)
        self.sections['activities'] = activity_section
        self.sections_layout.addWidget(activity_section)

        # 4. Tracking Section
        tracking_section = CollapsibleSection("Jahresmeldungen", icon_name="calendar", expanded=False)
        tracking_content = self._create_tracking_section()
        tracking_section.add_widget(tracking_content)
        self.sections['tracking'] = tracking_section
        self.sections_layout.addWidget(tracking_section)

        # Spacer am Ende
        self.sections_layout.addStretch()

    def _create_overview_content(self):
        """Erstellt den kombinierten Inhalt der Übersicht (KPIs + Actions)"""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setSpacing(AppleTheme.SPACING['lg'])
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 1: KPIs (Groß und prominent)
        kpi_grid = self._create_kpi_grid()
        layout.addWidget(kpi_grid)

        # Row 2: Schnellzugriffe (Zentriert und prominent)
        quick_actions = self._create_quick_actions()
        layout.addWidget(quick_actions)

        return container

    def _create_kpi_grid(self):
        """KPI Grid mit 4 Karten"""
        container = QtWidgets.QWidget()
        self.kpi_container_layout = QtWidgets.QHBoxLayout(container)
        layout = self.kpi_container_layout
        layout.setSpacing(AppleTheme.SPACING['md'])
        layout.setContentsMargins(0, 0, 0, 0)

        # KPI Daten abrufen
        depot_count = len(self.db.list_depots())
        praeparat_count = len(self.db.list_praeparate())

        # Bewegungen diesen Monat
        current_month = datetime.now().strftime("%Y-%m")
        bewegungen_query = """
            SELECT COUNT(*) FROM bewegungen
            WHERE strftime('%Y-%m', COALESCE(eingang_datum, ausgang_datum)) = ?
        """
        try:
            bewegungen_month = self.db.cur.execute(bewegungen_query, (current_month,)).fetchone()[0]
        except Exception:
            logger.debug("Bewegungen-Month-Query fehlgeschlagen, verwende Fallback 0")
            bewegungen_month = 0

        # Kritische Bestände
        kritisch_query = """
            SELECT COUNT(*) FROM (
                SELECT dp.depot_id, dp.praeparat_id, dp.sollbestand,
                    COALESCE(SUM(CASE
                        WHEN b.typ='Zugang' THEN b.anzahl
                        WHEN b.typ IN ('Abgang','Vernichtung') THEN -b.anzahl
                        ELSE 0 END), 0) as ist
                FROM depot_praeparate dp
                LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
                GROUP BY dp.depot_id, dp.praeparat_id, dp.sollbestand
                HAVING ist < dp.sollbestand
            )
        """
        kritisch_count = self.db.cur.execute(kritisch_query).fetchone()[0]

        # KPI Cards
        kpis = [
            {'icon': '', 'title': 'Depots', 'value': depot_count, 'color': AppleTheme.current_colors()['blue']},
            {'icon': '', 'title': 'Präparate', 'value': praeparat_count, 'color': AppleTheme.current_colors()['purple']},
            {'icon': '', 'title': 'Bewegungen (Monat)', 'value': bewegungen_month, 'color': AppleTheme.current_colors()['green']},
            {'icon': '', 'title': 'Unterbestände', 'value': kritisch_count, 'color': AppleTheme.current_colors()['red']},
        ]

        for kpi in kpis:
            card = self._create_kpi_card(
                icon=kpi['icon'],
                title=kpi['title'],
                value=kpi['value'],
                color=kpi['color']
            )
            layout.addWidget(card)

        return container

    def _create_kpi_card(self, icon, title, value, color):
        """Einzelne KPI Card - Größer und Prominenter"""
        card = QtWidgets.QFrame()
        card.setFrameShape(QtWidgets.QFrame.NoFrame)
        card.setMinimumHeight(150)
        card.setObjectName("kpi_card")

        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(AppleTheme.SPACING['sm'])
        layout.setContentsMargins(20, 20, 20, 20) # Mehr Padding

        # Title
        title_label = QtWidgets.QLabel(title.upper())
        title_label.setFont(AppleTheme.get_font('caption_1'))
        title_label.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; letter-spacing: 1px;")
        layout.addWidget(title_label)

        # Value
        value_label = QtWidgets.QLabel(str(value))
        value_label.setStyleSheet(f"""
            font-size: 38px;
            font-weight: 800;
            color: {color};
        """)
        layout.addWidget(value_label)

        layout.addStretch()

        return card

    def _create_quick_actions(self):
        """Schnellzugriffe Card - Einreihig und Premium-Design"""
        self.quick_access_container = create_card_widget()
        card = self.quick_access_container
        card.setMinimumHeight(0)

        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 18, 24, 18)

        # Titel
        self.quick_access_title = QtWidgets.QLabel("SCHNELLZUGRIFFE")
        self.quick_access_title.setFont(AppleTheme.get_font('caption1'))
        layout.addWidget(self.quick_access_title)

        # Responsive Flow-Layout für Buttons (ohne Überlappung).
        btn_container = QtWidgets.QWidget()
        btn_layout = FlowLayout(btn_container, margin=0, h_spacing=12, v_spacing=12)

        # Button Definitionen
        actions = [
            (" Neue Bewegung", 1, "activity"),
            (" Bericht erstellen", 3, "pie_chart"),
            (" Daten importieren", 4, "download"),
            (" E-Mail senden", 5, "mail"),
        ]

        self.quick_access_btns = []
        for text, pageidx, icon_name in actions:
            btn = QtWidgets.QPushButton(text)
            btn.setIcon(IconManager.get_icon(icon_name, color="white"))
            btn.setIconSize(QtCore.QSize(18, 18))
            btn.setMinimumHeight(48)
            btn.setMinimumWidth(180)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(AppleTheme.get_font('headline'))

            btn.clicked.connect(lambda checked=False, idx=pageidx: self.requestedPage.emit(idx))
            btn_layout.addWidget(btn)
            self.quick_access_btns.append(btn)

        layout.addWidget(btn_container)

        # Initial Styling anwenden
        self._update_quick_actions_style()

        return card


    def _create_verfall_section(self):
        """Verfallswarnungen Section - Nutzt externes VerfallWidget"""
        card = create_card_widget()
        # Keine feste Mindesthöhe hier, damit es responsiv bleibt
        card.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)

        card.setStyleSheet("QFrame { border: none; }")  # ← NEU!

        # Prüfe ob VerfallManager verfügbar ist
        if hasattr(self, 'verfallmanager') and self.verfallmanager:
            # Erstelle VerfallWidget
            self.verfall_widget = VerfallWidget(self.verfallmanager)

            # Verbinde Signal mit Dialog
            self.verfall_widget.detailsrequested.connect(self.show_verfall_details)

            layout.addWidget(self.verfall_widget)
        else:
            # Fallback wenn kein Manager verfügbar
            no_data = QtWidgets.QLabel("Verfallmanager nicht verfügbar")
            no_data.setAlignment(Qt.AlignCenter)
            no_data.setStyleSheet(f"""
                color: {AppleTheme.current_colors()['tertiary_label']};
                font-style: italic;
                padding: 30px;
            """)
            layout.addWidget(no_data)

        return card

    def show_verfall_details(self):
        """Öffnet Verfall-Details als integrierten Overlay-Dialog."""
        try:
            dialog = VerfallDetailDialog(self.verfallmanager, self)
            exec_embedded_dialog(self, dialog)
            if hasattr(self, "verfall_widget"):
                self.verfall_widget.refresh()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Fehler",
                f"Konnte Verfall-Details nicht öffnen:\n{str(e)}"
            )
            import logging
            logging.error(f"Fehler in show_verfall_details: {e}")

    def _create_activities_section(self):
        """Letzte Aktivitäten Section"""
        card = create_card_widget()
        card.setMinimumHeight(300)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md']
        )

        # Header mit Refresh Button
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("🕐 Letzte Aktivitäten")
        title.setFont(AppleTheme.get_font('headline'))
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.btn_refresh = QtWidgets.QPushButton("")
        self.btn_refresh.setIcon(IconManager.get_icon("refresh"))
        self.btn_refresh.setObjectName("btn_secondary")
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.clicked.connect(self.refresh_activities)
        header_layout.addWidget(self.btn_refresh)

        layout.addLayout(header_layout)

        # Scroll Area für Aktivitäten
        activity_scroll = QtWidgets.QScrollArea()
        activity_scroll.setWidgetResizable(True)
        activity_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        activity_scroll.setMinimumHeight(240)

        self.activity_widget = QtWidgets.QWidget()
        self.activity_layout = QtWidgets.QVBoxLayout(self.activity_widget)
        self.activity_layout.setSpacing(AppleTheme.SPACING['xs'])

        activity_scroll.setWidget(self.activity_widget)
        layout.addWidget(activity_scroll)

        return card

    def refresh_activities(self):
        """Lädt die letzten Bewegungen als Aktivitätenliste."""
        if not hasattr(self, "activity_layout"):
            return

        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            rows = self.db.list_bewegungen_with_attachments()[:12]
        except Exception as e:
            error_label = QtWidgets.QLabel(f"Aktivitäten konnten nicht geladen werden: {e}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet(f"color: {AppleTheme.current_colors()['status_red']};")
            self.activity_layout.addWidget(error_label)
            self.activity_layout.addStretch()
            return

        if not rows:
            empty_label = QtWidgets.QLabel("Noch keine Aktivitäten vorhanden.")
            empty_label.setStyleSheet(
                f"color: {AppleTheme.current_colors()['secondary_label']}; padding: 12px 8px;"
            )
            self.activity_layout.addWidget(empty_label)
            self.activity_layout.addStretch()
            return

        c = AppleTheme.current_colors()
        for row in rows:
            (
                _id,
                depot,
                praeparat,
                typ,
                _charge,
                _verfall,
                eingang,
                ausgang,
                empfaenger,
                anzahl,
                _pdf,
            ) = row

            when = eingang or ausgang or "-"
            if len(when) > 10:
                when = when[:10]

            item = QtWidgets.QFrame()
            item.setObjectName("activity_item")
            item.setStyleSheet(
                f"QFrame#activity_item {{ background-color: {c['bg_tertiary']}; border-radius: 10px; }}"
            )
            row_layout = QtWidgets.QHBoxLayout(item)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(10)

            typ_color = c["blue"]
            if typ == "Zugang":
                typ_color = c["green"]
            elif typ in ("Abgang", "Vernichtung"):
                typ_color = c["red"] if typ == "Vernichtung" else c["orange"]

            badge = QtWidgets.QLabel(typ)
            badge.setStyleSheet(
                f"background-color: {typ_color}22; color: {typ_color}; border-radius: 8px; "
                "padding: 3px 8px; font-weight: 600; min-width: 84px;"
            )
            badge.setAlignment(Qt.AlignCenter)
            row_layout.addWidget(badge)

            info = QtWidgets.QLabel(f"{depot} - {praeparat} - {anzahl} EH")
            info.setStyleSheet(f"color: {c['label']}; font-weight: 500;")
            info.setWordWrap(True)
            row_layout.addWidget(info, 1)

            meta_text = when
            if empfaenger:
                meta_text += f" | {empfaenger}"
            meta = QtWidgets.QLabel(meta_text)
            meta.setStyleSheet(f"color: {c['secondary_label']}; font-size: 12px;")
            meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row_layout.addWidget(meta)

            self.activity_layout.addWidget(item)

        self.activity_layout.addStretch()

    def _create_tracking_section(self):
        """Jahresmeldungen – Card-Design (Jahr über Spinbox)"""
        card = create_card_widget()
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md'],
            AppleTheme.SPACING['md']
        )

        # Header Bereich
        header_layout = QtWidgets.QHBoxLayout()

        # Linke Seite: Ring Chart
        self.completion_ring = CompletionRing(size=120)
        header_layout.addWidget(self.completion_ring)

        # Rechte Seite: Info + Jahr Auswahl
        info_layout = QtWidgets.QVBoxLayout()

        title_row = QtWidgets.QHBoxLayout()
        self.tracking_title = QtWidgets.QLabel("Jahresmeldungen")
        self.tracking_title.setFont(AppleTheme.get_font('title3'))
        title_row.addWidget(self.tracking_title)
        title_row.addStretch()

        self.spin_tracking_year = QtWidgets.QSpinBox()
        self.spin_tracking_year.setRange(2020, 2100)
        self.spin_tracking_year.setValue(datetime.now().year)
        self.spin_tracking_year.setFixedWidth(100)
        self.spin_tracking_year.valueChanged.connect(self.refresh_tracking)
        title_row.addWidget(self.spin_tracking_year)

        self.btn_refresh_tracking = QtWidgets.QPushButton("")
        self.btn_refresh_tracking.setIcon(IconManager.get_icon("refresh"))
        self.btn_refresh_tracking.setObjectName("btn_secondary")
        self.btn_refresh_tracking.setFixedSize(36, 36)
        self.btn_refresh_tracking.clicked.connect(self.refresh_tracking)
        title_row.addWidget(self.btn_refresh_tracking)

        info_layout.addLayout(title_row)

        self.summary_label = QtWidgets.QLabel("Status wird geladen...")
        self.summary_label.setFont(AppleTheme.get_font('subheadline'))
        self.summary_label.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']};")
        info_layout.addWidget(self.summary_label)

        info_layout.addStretch()

        # Bulk Actions Row
        bulk_layout = QtWidgets.QHBoxLayout()
        self.btn_mark_all_moves = QtWidgets.QPushButton("Alle Bewegungen")
        self.btn_mark_all_moves.setObjectName("btn_secondary")
        self.btn_mark_all_moves.clicked.connect(lambda: self._bulk_update_tracking('moves'))
        bulk_layout.addWidget(self.btn_mark_all_moves)

        self.btn_mark_all_stock = QtWidgets.QPushButton("Alle Bestände")
        self.btn_mark_all_stock.setObjectName("btn_secondary")
        self.btn_mark_all_stock.clicked.connect(lambda: self._bulk_update_tracking('stock'))
        bulk_layout.addWidget(self.btn_mark_all_stock)

        info_layout.addLayout(bulk_layout)
        header_layout.addLayout(info_layout)

        layout.addLayout(header_layout)
        layout.addSpacing(10)

        # Separator
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet(f"background-color: {AppleTheme.current_colors()['separator']}; max-height: 1px;")
        layout.addWidget(line)
        layout.addSpacing(10)

        # Kartengitter (Scrollbar für viele Depots)
        self.tracking_scroll = QtWidgets.QScrollArea()
        self.tracking_scroll.setWidgetResizable(True)
        self.tracking_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tracking_scroll.setMinimumHeight(240)

        self.tracking_cards_widget = QtWidgets.QWidget()
        self.tracking_cards_layout = QtWidgets.QVBoxLayout(self.tracking_cards_widget)
        self.tracking_cards_layout.setSpacing(12)
        self.tracking_cards_layout.setContentsMargins(0, 0, 0, 0)

        self.tracking_scroll.setWidget(self.tracking_cards_widget)
        layout.addWidget(self.tracking_scroll)

        return card

    def _bulk_update_tracking(self, type):
        """Aktualisiert alle Depots gleichzeitig"""
        year = self.spin_tracking_year.value()
        allowed_columns = {"bewegungen_erhalten", "bestand_erhalten"}
        column = "bewegungen_erhalten" if type == 'moves' else "bestand_erhalten"
        if column not in allowed_columns:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Ungültige Spalte: {column}")
            return

        try:
            self.db.cur.execute("UPDATE meldungs_tracking SET " + column + " = 1 WHERE jahr = ?", (year,))  # nosec B608: column is allow-list validated above
            self.db.conn.commit()
            self.refresh_tracking()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Fehler", f"Bulk Update fehlgeschlagen: {e}")


    def refresh_tracking(self):
        """Lädt Tracking-Cards neu mit optimiertem Design"""
        year = self.spin_tracking_year.value()
        self.tracking_title.setText("Jahresmeldungen")

        # Alte Karten entfernen
        while self.tracking_cards_layout.count():
            item = self.tracking_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        depots = self.db.list_depots()
        completed_count = 0
        total_steps = len(depots) * 2
        reached_steps = 0

        for row in depots:
            if len(row) < 2:
                continue
            depot_id = row[0]
            depot_name = row[1]
            # Tracking-Daten laden oder erstellen
            tracking_data = self.db.cur.execute("""
                SELECT bewegungen_erhalten, bestand_erhalten, notizen
                FROM meldungs_tracking
                WHERE depot_id = ? AND jahr = ?
            """, (depot_id, year)).fetchone()

            if not tracking_data:
                self.db.cur.execute("""
                    INSERT INTO meldungs_tracking (depot_id, jahr, bewegungen_erhalten, bestand_erhalten)
                    VALUES (?, ?, 0, 0)
                """, (depot_id, year))
                self.db.conn.commit()
                tracking_data = (0, 0, "")

            moves, stock, notes = tracking_data

            # Card erstellen
            card = TrackingCard(depot_id, depot_name, moves, stock, notes)
            card.status_changed.connect(self._save_tracking_change)
            self.tracking_cards_layout.addWidget(card)

            if moves:
                reached_steps += 1
            if stock:
                reached_steps += 1
            if moves and stock:
                completed_count += 1

        self.tracking_cards_layout.addStretch()

        # Progress Ring aktualisieren
        total_depots = len(depots)
        if total_steps > 0:
            percentage = (reached_steps / total_steps) * 100
            self.completion_ring.set_progress(percentage)
            self.summary_label.setText(f"Gesamtfortschritt: {completed_count} von {total_depots} Depots vollständig gemeldet.")
        else:
            self.completion_ring.set_progress(0)
            self.summary_label.setText("Keine Depots vorhanden.")

    def _save_tracking_change(self, depot_id, moves, stock):
        """Speichert Statusänderung einer Karte"""
        year = self.spin_tracking_year.value()
        card = self.sender()
        notes = card.notes_edit.text() if hasattr(card, 'notes_edit') else ""

        try:
            self.db.cur.execute("""
                UPDATE meldungs_tracking
                SET bewegungen_erhalten = ?, bestand_erhalten = ?, notizen = ?
                WHERE depot_id = ? AND jahr = ?
            """, (moves, stock, notes, depot_id, year))
            self.db.conn.commit()

            # Nur Progress updaten ohne Rebuild der Liste
            self._update_overall_progress()
        except Exception as e:
            print(f"Fehler beim Speichern des Tracking-Status: {e}")

    def _update_overall_progress(self):
        """Aktualisiert nur den Gesamtfortschritts-Ring (Performance!)"""
        year = self.spin_tracking_year.value()

        try:
            data = self.db.cur.execute("""
                SELECT SUM(bewegungen_erhalten), SUM(bestand_erhalten), COUNT(*)
                FROM meldungs_tracking
                WHERE jahr = ?
            """, (year,)).fetchone()

            if data and data[2] > 0:
                moves_sum, stock_sum, count = data
                moves_sum = moves_sum or 0
                stock_sum = stock_sum or 0

                total_steps = count * 2
                reached_steps = moves_sum + stock_sum

                percentage = (reached_steps / total_steps) * 100
                self.completion_ring.set_progress(percentage)

                # Check for full completion
                full_count = self.db.cur.execute("""
                    SELECT COUNT(*) FROM meldungs_tracking
                    WHERE jahr = ? AND bewegungen_erhalten = 1 AND bestand_erhalten = 1
                """, (year,)).fetchone()[0]

                self.summary_label.setText(f"Gesamtfortschritt: {full_count} von {count} Depots vollständig gemeldet.")
        except Exception as e:
            print(f"Fehler beim Progress-Update: {e}")
