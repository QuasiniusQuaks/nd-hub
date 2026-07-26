"""AppleDashboard section helpers (Issue #93)."""
from __future__ import annotations

import logging
from datetime import datetime

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from responsive_widgets import FlowLayout

from .widgets import (
    CollapsibleSection,
    create_card_widget,
)

logger = logging.getLogger(__name__)

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


