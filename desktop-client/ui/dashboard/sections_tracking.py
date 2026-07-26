"""AppleDashboard section helpers (Issue #93)."""
from __future__ import annotations

import logging
from datetime import datetime

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtWidgets

from .widgets import (
    CompletionRing,
    TrackingCard,
    create_card_widget,
)

logger = logging.getLogger(__name__)

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
