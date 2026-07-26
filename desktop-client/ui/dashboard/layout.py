"""AppleDashboard section helpers (Issue #93)."""
from __future__ import annotations

import logging

from apple_theme import AppleTheme
from PySide6 import QtWidgets

logger = logging.getLogger(__name__)

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

