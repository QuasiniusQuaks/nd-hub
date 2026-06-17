# -*- coding: utf-8 -*-
"""
VerfallWidget - Dashboard-Widget für Verfallsdatum-Warnungen
Version: 1.0 - Angepasst an bestehendes Verfall-System
"""

from PySide6 import QtWidgets, QtCore, QtGui
from verfallmanager import VerfallManager
from apple_theme import AppleTheme
import logging
from icon_manager import IconManager

logger = logging.getLogger(__name__)


class VerfallWidget(QtWidgets.QWidget):
    """
    Dashboard-Widget das verfallende Präparate anzeigt
    """

    # Signal wenn auf "Details anzeigen" geklickt wird
    detailsrequested = QtCore.Signal()

    def __init__(self, verfallmanager: VerfallManager, parent=None):
        super().__init__(parent)
        self.verfallmanager = verfallmanager

        self._setup_ui()
        self.refresh()

    def refresh_theme(self):
        """Aktualisiert das Widget bei Themenwechsel"""
        c = AppleTheme.current_colors()
        if hasattr(self, 'card'):
            self.card.setStyleSheet(f"QWidget {{ background-color: {c['bg_secondary']}; }}")
            self.card.style().unpolish(self.card)
            self.card.style().polish(self.card)
            
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {c['bg_tertiary']}; border: none; border-radius: 8px; font-size: 16px; }}
                QPushButton:hover {{ background-color: {c['hover']}; }}
            """)
            
        if hasattr(self, 'list_widget'):
            self.list_widget.setStyleSheet(f"""
                QListWidget {{ background-color: {c['bg_tertiary']}; border: 1px solid {c['separator']}; border-radius: 8px; font-size: 13px; }}
                QListWidget::item {{ padding: 8px 12px; border-bottom: 1px solid {c['separator']}; }}
                QListWidget::item:hover {{ background-color: {c['hover']}; }}
            """)
            
        if hasattr(self, 'details_btn'):
            self.details_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {c['blue']}; color: white; border: none; border-radius: 8px; padding: 10px; font-weight: 600; font-size: 14px; }}
                QPushButton:hover {{ background-color: {c['blue']}cc; }}
            """)
            
        self.refresh()
        self.update()

    def _setup_ui(self):
        """Erstellt das User Interface"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Card-Widget
        card = self._create_card()
        layout.addWidget(card)

    def _create_card(self) -> QtWidgets.QWidget:
        """Erstellt die Karte mit den Warnungen"""
        self.card = QtWidgets.QWidget()
        self.card.setMinimumHeight(550)
        c = AppleTheme.current_colors()
        self.card.setStyleSheet(f"""
            QWidget {{
                background-color: {c['bg_secondary']};
            }}
        """)

        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # Header
        header_layout = QtWidgets.QHBoxLayout()

        title = QtWidgets.QLabel("Verfallende Präparate")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {c['label']};
        """)
        header_layout.addWidget(title)

        # Refresh-Button
        self.refresh_btn = QtWidgets.QPushButton("")
        self.refresh_btn.setIcon(IconManager.get_icon("refresh"))
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        self.refresh_btn.setToolTip("Aktualisieren")
        self.refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_btn)

        header_layout.addStretch()
        card_layout.addLayout(header_layout)

        # Statistik-Boxen
        stats_layout = QtWidgets.QHBoxLayout()
        stats_layout.setSpacing(12)

        # Kritisch (Rot)
        self.kritisch_box = self._create_stat_box(
            "Kritisch",
            "0",
            "< 30 Tage",
            "#dc3545"
        )
        stats_layout.addWidget(self.kritisch_box)

        # Warnung (Orange)
        self.warnung_box = self._create_stat_box(
            "Warnung",
            "0",
            "< 90 Tage",
            "#fd7e14"
        )
        stats_layout.addWidget(self.warnung_box)

        # Achtung (Gelb)
        self.achtung_box = self._create_stat_box(
            "Achtung",
            "0",
            "< 180 Tage",
            "#ffc107"
        )
        stats_layout.addWidget(self.achtung_box)

        card_layout.addLayout(stats_layout)

        # Nächste Verfälle
        next_label = QtWidgets.QLabel("🔜 Nächste Verfälle:")
        next_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {c['label']};
            margin-top: 8px;
        """)
        card_layout.addWidget(next_label)

        # Liste
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setMinimumHeight(400)
        self.list_widget.setMaximumHeight(800)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {c['bg_tertiary']};
                border: 1px solid {c['separator']};
                border-radius: 8px;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {c['separator']};
            }}
            QListWidget::item:hover {{
                background-color: {c['hover']};
            }}
        """)
        card_layout.addWidget(self.list_widget)

        # Details-Button
        self.details_btn = QtWidgets.QPushButton("📋 Alle Details anzeigen")
        self.details_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['blue']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {c['blue']}cc;
            }}
            QPushButton:pressed {{
                background-color: {c['blue']}99;
            }}
        """)
        self.details_btn.clicked.connect(self.detailsrequested.emit)
        card_layout.addWidget(self.details_btn)

        return self.card

    def _create_stat_box(self, title: str, value: str, subtitle: str, color: str) -> QtWidgets.QWidget:
        """
        Erstellt eine Statistik-Box

        Args:
            title: Titel (z.B. "Kritisch")
            value: Wert (Anzahl)
            subtitle: Untertitel (z.B. "< 30 Tage")
            color: Farbe (Hex)

        Returns:
            Widget mit der Statistik
        """
        box = QtWidgets.QFrame()
        box.setObjectName(f"stat_box_{title.lower()}")
        box.setMinimumHeight(140)
        box.setMinimumWidth(120)
        box.setStyleSheet(f"""
            QFrame#{"stat_box_" + title.lower()} {{
                background-color: {color};
                border-radius: 12px;
                padding: 12px;
            }}
        """)

        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(4)

        # Titel
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("""
            color: white;
            font-size: 12px;
            font-weight: 600;
            background: transparent;
        """)
        layout.addWidget(title_label)

        # Wert
        value_label = QtWidgets.QLabel(value)
        value_label.setObjectName(f"{title.lower()}_value")
        value_label.setStyleSheet("""
            color: white;
            font-size: 28px;
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(value_label)

        # Untertitel
        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.85);
            font-size: 11px;
            background: transparent;
        """)
        layout.addWidget(subtitle_label)

        layout.addStretch()

        return box

    def refresh(self):
        """Aktualisiert die Anzeige"""
        try:
            # Hole Statistiken
            stats = self.verfallmanager.getstatistics()

            # Aktualisiere Statistik-Boxen
            self.kritisch_box.findChild(QtWidgets.QLabel, "kritisch_value").setText(
                str(stats['kritisch'])
            )
            self.warnung_box.findChild(QtWidgets.QLabel, "warnung_value").setText(
                str(stats['warnung'])
            )
            self.achtung_box.findChild(QtWidgets.QLabel, "achtung_value").setText(
                str(stats['achtung'])
            )

            # Aktualisiere Liste
            self.list_widget.clear()
            naechste = self.verfallmanager.getnaechsteverfaelle(limit=5)

            if not naechste:
                item = QtWidgets.QListWidgetItem("✅ Keine verfallenden Präparate")
                item.setForeground(QtGui.QColor("#28a745"))
                self.list_widget.addItem(item)
            else:
                for praeparat in naechste:
                    # Erstelle Item-Text
                    text = (
                        f"{praeparat['praeparat_name']} - "
                        f"{praeparat['depot_name']} - "
                        f"{praeparat['tage_bis_verfall']} Tage"
                    )

                    item = QtWidgets.QListWidgetItem(text)

                    # Setze Farbe basierend auf Kategorie - mit starkem Kontrast
                    c = AppleTheme.current_colors()
                    if praeparat['kategorie'] == 'kritisch':
                        item.setForeground(QtGui.QColor(c['red']))
                        text = f"🔴  {text}"
                        item.setText(text)
                    elif praeparat['kategorie'] == 'warnung':
                        item.setForeground(QtGui.QColor(c['orange']))
                        text = f"🟠  {text}"
                        item.setText(text)
                    else:
                        # Gelb ist auf Weiß kaum lesbar - verwende stattdessen einen kräftigeren Braunton
                        item.setForeground(QtGui.QColor("#b8860b"))  # DarkGoldenrod - immer gut lesbar
                        text = f"🟡  {text}"
                        item.setText(text)

                    self.list_widget.addItem(item)

            logger.info("VerfallWidget aktualisiert")

        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des VerfallWidget: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Fehler",
                f"Fehler beim Laden der Daten:\n{str(e)}"
            )


class VerfallIndicator(QtWidgets.QWidget):
    """
    Kleiner Indikator für die Sidebar oder Statusleiste
    Zeigt nur die Anzahl kritischer Präparate
    """

    clicked = QtCore.Signal()

    def __init__(self, verfallmanager: VerfallManager, parent=None):
        super().__init__(parent)
        self.verfallmanager = verfallmanager

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Icon
        self.icon_label = QtWidgets.QLabel("")
        self.icon_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.icon_label)

        # Text
        c = AppleTheme.current_colors()

        # Text
        self.text_label = QtWidgets.QLabel("0")
        self.text_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {c['red']};
        """)
        layout.addWidget(self.text_label)

        # Tooltip
        self.setToolTip("Verfallende Präparate")

        # Mach klickbar
        self.setCursor(QtCore.Qt.PointingHandCursor)

        # Style
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {c['orange']}22;
                border-radius: 8px;
            }}
            QWidget:hover {{
                background-color: {c['orange']}44;
            }}
        """)

        self.refresh()

    def refresh(self):
        """Aktualisiert den Indikator"""
        try:
            stats = self.verfallmanager.getstatistics()
            kritisch = stats['kritisch']
            gesamt = stats['gesamt']

            if kritisch > 0:
                self.text_label.setText(str(kritisch))
                self.icon_label.setText("🔴")
                self.setToolTip(f"{kritisch} kritische Präparate (< 30 Tage)")
            elif gesamt > 0:
                self.text_label.setText(str(gesamt))
                self.icon_label.setText("")
                self.setToolTip(f"{gesamt} verfallende Präparate")
            else:
                self.text_label.setText("")
                self.icon_label.setText("✅")
                self.setToolTip("Keine verfallenden Präparate")
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des VerfallIndicator: {e}")

    def mousePressEvent(self, event):
        """Behandelt Klick-Events"""
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
