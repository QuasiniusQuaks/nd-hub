"""Globale Filter-Leiste — sticky oben im Analytics Control Center.

Zeigt: Zeitraum-Picker (7T / 30T / 90T / 1J / Custom), Depot-Filter,
Präparat-Filter und Refresh-Button. Wirkt auf alle Tabs und Charts.

Issue #42 Phase 1 — Tab-Layer.
"""

from __future__ import annotations

import logging

from apple_theme import AppleTheme
from db_manager import Database
from PySide6 import QtCore, QtWidgets

from .cross_filter_state import CrossFilterState

logger = logging.getLogger(__name__)

# Zeitraum-Optionen: (Label, Tage)
_DATE_RANGES = [
    ("7 Tage", 7),
    ("30 Tage", 30),
    ("90 Tage", 90),
    ("1 Jahr", 365),
]


class GlobalFilterBar(QtWidgets.QWidget):
    """Sticky Filter-Leiste mit Zeitraum-Picker, Depot- und Präparat-Filter."""

    filtersChanged = QtCore.Signal()

    def __init__(self, db: Database, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.filter_state = CrossFilterState.instance()

        self.setObjectName("filter_bar")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self._apply_style()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Zeitraum-Picker
        lbl_zeit = QtWidgets.QLabel("Zeitraum:")
        c = AppleTheme.current_colors()
        lbl_zeit.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['secondary_label']};")
        layout.addWidget(lbl_zeit)

        self.combo_zeitraum = QtWidgets.QComboBox()
        for label, days in _DATE_RANGES:
            self.combo_zeitraum.addItem(label, days)
        self.combo_zeitraum.setCurrentIndex(1)  # Default: 30 Tage
        self.combo_zeitraum.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.combo_zeitraum)

        # Separator
        layout.addWidget(self._make_separator())

        # Depot-Filter (Multi-Select ComboBox — vereinfacht als Checkable ComboBox)
        lbl_depot = QtWidgets.QLabel("Depots:")
        lbl_depot.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['secondary_label']};")
        layout.addWidget(lbl_depot)

        self.combo_depot = self._create_multi_select_combo("Alle Depots")
        self._populate_depot_combo()
        layout.addWidget(self.combo_depot)

        # Präparat-Filter
        lbl_praep = QtWidgets.QLabel("Präparate:")
        lbl_praep.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['secondary_label']};")
        layout.addWidget(lbl_praep)

        self.combo_praeparat = self._create_multi_select_combo("Alle Präparate")
        self._populate_praeparat_combo()
        layout.addWidget(self.combo_praeparat)

        layout.addStretch()

        # Vergleichs-Modus Toggle (Phase 2)
        self.btn_compare = QtWidgets.QPushButton("📊 vs. Vorjahr")
        self.btn_compare.setCheckable(True)
        self.btn_compare.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_compare.setToolTip("Vergleichs-Modus: aktuelle Periode vs. Vorjahr")
        self.btn_compare.clicked.connect(self._on_compare_toggled)
        layout.addWidget(self.btn_compare)

        # Saved Views (Phase 2)
        layout.addWidget(self._make_separator())
        lbl_views = QtWidgets.QLabel("Views:")
        lbl_views.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['secondary_label']};")
        layout.addWidget(lbl_views)

        self.combo_saved_views = QtWidgets.QComboBox()
        self.combo_saved_views.addItem("— Gespeicherte Views —")
        self._populate_saved_views()
        self.combo_saved_views.currentIndexChanged.connect(self._on_view_selected)
        layout.addWidget(self.combo_saved_views)

        self.btn_save_view = QtWidgets.QPushButton("💾 Speichern")
        self.btn_save_view.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_save_view.clicked.connect(self._on_save_view)
        layout.addWidget(self.btn_save_view)

        self.btn_delete_view = QtWidgets.QPushButton("🗑️")
        self.btn_delete_view.setMaximumWidth(36)
        self.btn_delete_view.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_delete_view.clicked.connect(self._on_delete_view)
        layout.addWidget(self.btn_delete_view)

        # Export-Buttons (Phase 3)
        layout.addWidget(self._make_separator())
        self.btn_export_html = QtWidgets.QPushButton("🌐 HTML")
        self.btn_export_html.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_export_html.setToolTip("Als interaktives HTML exportieren")
        self.btn_export_html.clicked.connect(self._on_export_html)
        layout.addWidget(self.btn_export_html)

        self.btn_export_pdf = QtWidgets.QPushButton("📄 PDF")
        self.btn_export_pdf.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.setToolTip("Als PDF-Report exportieren")
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        layout.addWidget(self.btn_export_pdf)

        # Refresh-Button
        self.btn_refresh = QtWidgets.QPushButton("↻ Aktualisieren")
        self.btn_refresh.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._on_refresh)
        layout.addWidget(self.btn_refresh)

    def _apply_style(self) -> None:
        c = AppleTheme.current_colors()
        self.setStyleSheet(
            f"""
            #filter_bar {{
                background-color: {c.get('card_bg', c.get('background', '#ffffff'))};
                border-bottom: 1px solid {c.get('separator', '#e0e0e0')};
            }}
            """
        )

    def _make_separator(self) -> QtWidgets.QFrame:
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setFixedWidth(1)
        c = AppleTheme.current_colors()
        sep.setStyleSheet(f"color: {c.get('separator', '#e0e0e0')};")
        return sep

    def _create_multi_select_combo(self, placeholder: str) -> QtWidgets.QComboBox:
        """Erstellt eine vereinfachte Multi-Select-ComboBox (Phase 1: single-select)."""
        combo = QtWidgets.QComboBox()
        combo.addItem(placeholder)
        combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        combo.setMinimumWidth(120)
        return combo

    def _populate_depot_combo(self) -> None:
        """Lädt alle Depots in die ComboBox."""
        try:
            rows = self.db.cur.execute("SELECT id, name FROM depots ORDER BY name").fetchall()
            for row in rows:
                self.combo_depot.addItem(f"  {row[1]}", row[0])
        except Exception:
            logger.exception("Depot-Combo-Population fehlgeschlagen")

    def _populate_praeparat_combo(self) -> None:
        """Lädt alle Präparate in die ComboBox."""
        try:
            rows = self.db.cur.execute("SELECT id, name FROM praeparate ORDER BY name").fetchall()
            for row in rows:
                self.combo_praeparat.addItem(f"  {row[1]}", row[0])
        except Exception:
            logger.exception("Präparat-Combo-Population fehlgeschlagen")

    def _on_filter_changed(self) -> None:
        """Filter geändert → CrossFilterState updaten + Signal emit."""
        days = self.combo_zeitraum.currentData()
        self.filter_state.set_date_range(days)
        self.filtersChanged.emit()

    def _on_refresh(self) -> None:
        """Refresh-Button → Signal emit (Page lädt alle Tabs neu)."""
        self.filtersChanged.emit()

    def get_date_range_days(self) -> int:
        """Gibt den aktuell gewählten Zeitraum in Tagen zurück."""
        return self.combo_zeitraum.currentData() or 30

    def refresh_theme(self) -> None:
        """Bei Theme-Wechsel neu stylen."""
        self._apply_style()

    # ── Vergleichs-Modus (Phase 2) ──────────────────────────────────

    def _on_compare_toggled(self) -> None:
        """Vergleichs-Modus Toggle → Signal emit."""
        self.filtersChanged.emit()

    def is_compare_mode(self) -> bool:
        """True wenn Vergleichs-Modus aktiv ist."""
        return self.btn_compare.isChecked()

    # ── Saved Views (Phase 2) ───────────────────────────────────────

    def _populate_saved_views(self) -> None:
        """Lädt gespeicherte Views in die ComboBox."""
        self.combo_saved_views.clear()
        self.combo_saved_views.addItem("— Gespeicherte Views —")
        try:
            views = self.db.get_analytics_views()
            for view in views:
                self.combo_saved_views.addItem(str(view["name"]), view["filter_json"])
        except Exception:
            logger.debug("Saved-Views-Population fehlgeschlagen (Tabelle evtl. nicht vorhanden)")

    def _on_view_selected(self, index: int) -> None:
        """View ausgewählt → Filter aus JSON laden + anwenden."""
        if index <= 0:
            return
        filter_json = self.combo_saved_views.itemData(index)
        if not filter_json:
            return
        try:
            import json
            config = json.loads(filter_json)

            # Zeitraum setzen
            days = config.get("date_range_days", 30)
            for i in range(self.combo_zeitraum.count()):
                if self.combo_zeitraum.itemData(i) == days:
                    self.combo_zeitraum.setCurrentIndex(i)
                    break

            # Vergleichs-Modus
            self.btn_compare.setChecked(config.get("compare_mode", False))

            # Cross-Filter setzen
            depot_ids = set(config.get("depot_ids", []))
            praeparat_ids = set(config.get("praeparat_ids", []))
            self.filter_state.set_depot_filter(depot_ids)
            self.filter_state.set_praeparat_filter(praeparat_ids)

            self.filtersChanged.emit()
        except Exception:
            logger.exception("Saved-View-Laden fehlgeschlagen")

    def _on_save_view(self) -> None:
        """Aktuelle Filter-Konfiguration als View speichern."""
        from PySide6 import QtWidgets as QW

        name, ok = QW.QInputDialog.getText(
            self, "View speichern", "Name der View:", text=""
        )
        if not ok or not name.strip():
            return

        import json
        config = {
            "date_range_days": self.get_date_range_days(),
            "compare_mode": self.is_compare_mode(),
            "depot_ids": list(self.filter_state.state.depot_ids),
            "praeparat_ids": list(self.filter_state.state.praeparat_ids),
        }
        filter_json = json.dumps(config)

        success = self.db.save_analytics_view(name.strip(), filter_json)
        if success:
            self._populate_saved_views()
            QW.QMessageBox.information(self, "Gespeichert", f"View '{name}' gespeichert.")
        else:
            QW.QMessageBox.warning(self, "Fehler", f"View '{name}' konnte nicht gespeichert werden.")

    def _on_delete_view(self) -> None:
        """Aktuell ausgewählte View löschen."""
        from PySide6 import QtWidgets as QW

        index = self.combo_saved_views.currentIndex()
        if index <= 0:
            return
        name = self.combo_saved_views.itemText(index)

        reply = QW.QMessageBox.question(
            self, "Löschen", f"View '{name}' wirklich löschen?",
            QW.QMessageBox.Yes | QW.QMessageBox.No,
        )
        if reply != QW.QMessageBox.Yes:
            return

        self.db.delete_analytics_view(name)
        self._populate_saved_views()

    # ── Export (Phase 3) ────────────────────────────────────────────

    def _on_export_html(self) -> None:
        """HTML-Export via File-Dialog."""
        from PySide6 import QtWidgets as QW

        from .._insights.html_export import HTMLExporter

        path, _ = QW.QFileDialog.getSaveFileName(
            self, "HTML exportieren", "analytics_report.html",
            "HTML-Dateien (*.html);;Alle Dateien (*)",
            options=QW.QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return

        exporter = HTMLExporter(self.db)
        days = self.get_date_range_days()
        if exporter.export(path, days=days):
            QW.QMessageBox.information(self, "Export erfolgreich",
                                       f"HTML-Report gespeichert:\n{path}")
        else:
            QW.QMessageBox.warning(self, "Export fehlgeschlagen",
                                   "HTML-Report konnte nicht erstellt werden.")

    def _on_export_pdf(self) -> None:
        """PDF-Export via File-Dialog."""
        from PySide6 import QtWidgets as QW

        from .._insights.pdf_report import PDFReporter

        path, _ = QW.QFileDialog.getSaveFileName(
            self, "PDF exportieren", "analytics_report.pdf",
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
            options=QW.QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return

        reporter = PDFReporter(self.db)
        days = self.get_date_range_days()
        if reporter.export(path, days=days):
            QW.QMessageBox.information(self, "Export erfolgreich",
                                       f"PDF-Report gespeichert:\n{path}")
        else:
            QW.QMessageBox.warning(self, "Export fehlgeschlagen",
                                   "PDF-Report konnte nicht erstellt werden.")

