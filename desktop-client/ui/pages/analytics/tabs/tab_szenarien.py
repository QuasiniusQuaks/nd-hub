"""Szenario-Builder — individuelle Auswertungen per Dropdown (ohne SQL).

Ermöglicht die Zusammenstellung von Auswertungen zu bestimmten
Depots und/oder Präparaten über geführte Auswahlfelder.

Ersetzt den SQL-Tab im Analytics Control Center.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from apple_theme import AppleTheme

from ._base_tab import BaseTab

logger = logging.getLogger(__name__)

_SCENARIO_TYPES = [
    ("Bestand Soll/Ist", "bestand"),
    ("Verfallwarnungen", "verfall"),
    ("Bewegungsanalyse", "bewegungen"),
    ("Depot-Ranking (Abgaben)", "depot_ranking"),
    ("Präparat-Ranking (Abgaben)", "praeparat_ranking"),
    ("Toter Bestand", "dead_stock"),
    ("Lagerumschlag", "turnover"),
    ("Verfall-Forecast", "verfall_forecast"),
]

_TIME_RANGES = [
    ("7 Tage", 7),
    ("30 Tage", 30),
    ("90 Tage", 90),
    ("1 Jahr", 365),
    ("Gesamter Zeitraum", 0),
]


def _row_val(row, key, default=None, idx=None):
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
        if idx is not None and isinstance(row, (tuple, list)):
            return row[idx]
        return row[key]
    except Exception:
        return default


class TabSzenarien(BaseTab):
    """Geführte Auswertungs-Szenarien mit Dropdown-Auswahl."""

    def __init__(self, db, queries, parent=None) -> None:
        super().__init__(db, queries, parent)
        self._last_headers: list[str] = []
        self._last_rows: list = []

    def refresh(self) -> None:
        prev_type = getattr(self, "combo_type", None)
        prev_type_key = prev_type.currentData() if prev_type else None

        self._clear_content()
        c = AppleTheme.current_colors()

        card = self._make_card("🧩 Auswertungs-Szenario zusammenstellen")
        form = QtWidgets.QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.combo_type = QtWidgets.QComboBox()
        for label, key in _SCENARIO_TYPES:
            self.combo_type.addItem(label, key)
        if prev_type_key is not None:
            idx = self.combo_type.findData(prev_type_key)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
        self.combo_type.setMinimumHeight(36)
        form.addRow("Auswertungstyp:", self.combo_type)

        self.combo_depot = QtWidgets.QComboBox()
        self.combo_depot.setMinimumHeight(36)
        self.combo_depot.setMinimumContentsLength(24)
        form.addRow("Depot:", self.combo_depot)

        self.combo_praeparat = QtWidgets.QComboBox()
        self.combo_praeparat.setMinimumHeight(36)
        self.combo_praeparat.setMinimumContentsLength(24)
        form.addRow("Präparat:", self.combo_praeparat)

        self.combo_zeit = QtWidgets.QComboBox()
        for label, days in _TIME_RANGES:
            self.combo_zeit.addItem(label, days)
        self.combo_zeit.setCurrentIndex(1)
        self.combo_zeit.setMinimumHeight(36)
        form.addRow("Zeitraum:", self.combo_zeit)

        multi_box = QtWidgets.QHBoxLayout()
        self.list_depots = QtWidgets.QListWidget()
        self.list_depots.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.list_depots.setMinimumHeight(110)
        self.list_depots.setToolTip("Optional: mehrere Depots (überschreibt Einzel-Dropdown)")
        self.list_praeps = QtWidgets.QListWidget()
        self.list_praeps.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.list_praeps.setMinimumHeight(110)
        self.list_praeps.setToolTip("Optional: mehrere Präparate (überschreibt Einzel-Dropdown)")

        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("Mehrere Depots (optional):"))
        left.addWidget(self.list_depots)
        right = QtWidgets.QVBoxLayout()
        right.addWidget(QtWidgets.QLabel("Mehrere Präparate (optional):"))
        right.addWidget(self.list_praeps)
        multi_box.addLayout(left, 1)
        multi_box.addLayout(right, 1)

        card.layout().addLayout(form)
        card.layout().addLayout(multi_box)

        hint = QtWidgets.QLabel(
            "Tipp: Einzelauswahl über Dropdowns — oder mehrere Einträge in den Listen markieren. "
            "Leere Mehrfachauswahl = Dropdown greift."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {c['secondary_label']}; font-size: 12px;")
        card.layout().addWidget(hint)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("▶ Auswertung starten")
        self.btn_run.setObjectName("btn_save")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.clicked.connect(self._run_scenario)
        btn_row.addWidget(self.btn_run)

        self.btn_reset = QtWidgets.QPushButton("Zurücksetzen")
        self.btn_reset.setObjectName("btn_secondary")
        self.btn_reset.setMinimumHeight(40)
        self.btn_reset.clicked.connect(self._reset_filters)
        btn_row.addWidget(self.btn_reset)
        btn_row.addStretch()
        card.layout().addLayout(btn_row)

        result_card = self._make_card("📊 Ergebnis")
        self.lbl_result_meta = QtWidgets.QLabel("Noch keine Auswertung ausgeführt.")
        self.lbl_result_meta.setWordWrap(True)
        self.lbl_result_meta.setStyleSheet(f"color: {c['secondary_label']}; font-size: 12px;")
        result_card.layout().addWidget(self.lbl_result_meta)

        self.result_table = self._create_responsive_table([], 0)
        self.result_table.setMinimumHeight(280)
        result_card.layout().addWidget(self.result_table)

        export_row = QtWidgets.QHBoxLayout()
        self.btn_export = QtWidgets.QPushButton("📋 In Zwischenablage kopieren")
        self.btn_export.setObjectName("btn_secondary")
        self.btn_export.clicked.connect(self._copy_results)
        export_row.addWidget(self.btn_export)
        export_row.addStretch()
        result_card.layout().addLayout(export_row)

        self.content_layout.addStretch()
        self._populate_master_data()

        if self._last_headers:
            self._fill_table(self._last_headers, self._last_rows)

    def _populate_master_data(self) -> None:
        self.combo_depot.clear()
        self.combo_praeparat.clear()
        self.list_depots.clear()
        self.list_praeps.clear()

        self.combo_depot.addItem("Alle Depots", None)
        self.combo_praeparat.addItem("Alle Präparate", None)

        try:
            for row in self.db.cur.execute("SELECT id, name FROM depots ORDER BY name").fetchall():
                did = _row_val(row, "id", idx=0)
                name = str(_row_val(row, "name", idx=1) or "")
                self.combo_depot.addItem(name, did)
                item = QtWidgets.QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, did)
                self.list_depots.addItem(item)
        except Exception:
            logger.exception("Depots laden fehlgeschlagen")

        try:
            for row in self.db.cur.execute("SELECT id, name FROM praeparate ORDER BY name").fetchall():
                pid = _row_val(row, "id", idx=0)
                name = str(_row_val(row, "name", idx=1) or "")
                self.combo_praeparat.addItem(name, pid)
                item = QtWidgets.QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, pid)
                self.list_praeps.addItem(item)
        except Exception:
            logger.exception("Präparate laden fehlgeschlagen")

    def _reset_filters(self) -> None:
        self.combo_type.setCurrentIndex(0)
        self.combo_depot.setCurrentIndex(0)
        self.combo_praeparat.setCurrentIndex(0)
        self.combo_zeit.setCurrentIndex(1)
        self.list_depots.clearSelection()
        self.list_praeps.clearSelection()
        self.lbl_result_meta.setText("Filter zurückgesetzt.")
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self._last_headers, self._last_rows = [], []

    def _selected_depot_ids(self) -> list[int] | None:
        multi = [
            it.data(Qt.ItemDataRole.UserRole)
            for it in self.list_depots.selectedItems()
            if it.data(Qt.ItemDataRole.UserRole) is not None
        ]
        if multi:
            return multi
        val = self.combo_depot.currentData()
        return [val] if val is not None else None

    def _selected_praeparat_ids(self) -> list[int] | None:
        multi = [
            it.data(Qt.ItemDataRole.UserRole)
            for it in self.list_praeps.selectedItems()
            if it.data(Qt.ItemDataRole.UserRole) is not None
        ]
        if multi:
            return multi
        val = self.combo_praeparat.currentData()
        return [val] if val is not None else None

    def _selected_names(self, which: str) -> set[str]:
        names: set[str] = set()
        if which == "depot":
            ids = self._selected_depot_ids()
            if not ids:
                return names
            for i in range(self.combo_depot.count()):
                if self.combo_depot.itemData(i) in ids:
                    names.add(self.combo_depot.itemText(i))
            for it in self.list_depots.selectedItems():
                names.add(it.text())
        else:
            ids = self._selected_praeparat_ids()
            if not ids:
                return names
            for i in range(self.combo_praeparat.count()):
                if self.combo_praeparat.itemData(i) in ids:
                    names.add(self.combo_praeparat.itemText(i))
            for it in self.list_praeps.selectedItems():
                names.add(it.text())
        return names

    def _date_range(self) -> tuple[str | None, str | None, int]:
        days = int(self.combo_zeit.currentData() or 0)
        if days <= 0:
            return None, None, 0
        end = date.today()
        start = end - timedelta(days=days)
        return start.isoformat(), end.isoformat(), days

    def _run_scenario(self) -> None:
        key = self.combo_type.currentData()
        depot_ids = self._selected_depot_ids()
        praeparat_ids = self._selected_praeparat_ids()
        start, end, days = self._date_range()
        days_eff = days or 30

        try:
            headers, rows, meta = self._execute(key, depot_ids, praeparat_ids, start, end, days_eff)
        except Exception as exc:
            logger.exception("Szenario-Auswertung fehlgeschlagen")
            QtWidgets.QMessageBox.warning(self, "Auswertung", f"Fehler: {exc}")
            return

        self._last_headers, self._last_rows = headers, rows
        self._fill_table(headers, rows)
        self.lbl_result_meta.setText(
            f"{meta} · {len(rows)} Zeile(n) · "
            f"Depot-Filter: {'alle' if not depot_ids else len(depot_ids)} · "
            f"Präparat-Filter: {'alle' if not praeparat_ids else len(praeparat_ids)}"
        )

    def _filter_rows_by_names(self, rows, depot_col=None, praep_col=None, depot_ids=None, praeparat_ids=None):
        depot_names = self._selected_names("depot") if depot_ids else set()
        praep_names = self._selected_names("praeparat") if praeparat_ids else set()
        out = []
        for row in rows:
            if depot_names and depot_col is not None and str(row[depot_col]) not in depot_names:
                continue
            if praep_names and praep_col is not None and str(row[praep_col]) not in praep_names:
                continue
            out.append(row)
        return out

    def _execute(self, key, depot_ids, praeparat_ids, start, end, days):
        q = self.queries

        if key == "bestand":
            raw = q.get_bestandsentwicklung(depot_ids=depot_ids, praeparat_ids=praeparat_ids)
            headers = ["Depot", "Präparat", "Soll", "Ist", "Differenz"]
            rows = [
                [
                    _row_val(r, "depot_name", idx=0),
                    _row_val(r, "praeparat_name", idx=1),
                    _row_val(r, "sollbestand", idx=2),
                    _row_val(r, "ist_bestand", idx=3),
                    _row_val(r, "differenz", idx=4),
                ]
                for r in raw
            ]
            return headers, rows, "Bestand Soll/Ist"

        if key == "verfall":
            raw = q.get_verfall_warnings(days=days)
            headers = ["Depot", "Präparat", "PZN", "Menge", "Verfall", "Status"]
            rows = []
            for r in raw:
                did = _row_val(r, "depot_id")
                pid = _row_val(r, "praeparat_id")
                if depot_ids and did is not None and did not in depot_ids:
                    continue
                if praeparat_ids and pid is not None and pid not in praeparat_ids:
                    continue
                rows.append(
                    [
                        _row_val(r, "depot_name", default="—"),
                        _row_val(r, "praeparat_name", default="—"),
                        _row_val(r, "pzn", default=""),
                        _row_val(r, "menge", default=_row_val(r, "anzahl", default="")),
                        _row_val(r, "verfallsdatum", default=_row_val(r, "verfall", default="")),
                        _row_val(r, "status", default=""),
                    ]
                )
            # name fallback if ids missing on rows
            if (depot_ids or praeparat_ids) and rows and all(r[0] == "—" or True for r in rows):
                rows = self._filter_rows_by_names(
                    rows, depot_col=0, praep_col=1, depot_ids=depot_ids, praeparat_ids=praeparat_ids
                )
            return headers, rows, f"Verfallwarnungen ({days} Tage)"

        if key == "bewegungen":
            raw = q.get_bewegungen_analyse(
                depot_ids=depot_ids, praeparat_ids=praeparat_ids, start_date=start, end_date=end
            )
            headers = ["Depot", "Präparat", "Typ", "Monat", "Gesamt"]
            rows = [
                [
                    _row_val(r, "depot_name", idx=0),
                    _row_val(r, "praeparat_name", idx=1),
                    _row_val(r, "typ", idx=2),
                    _row_val(r, "monat", idx=3),
                    _row_val(r, "gesamt", idx=4),
                ]
                for r in raw
            ]
            return headers, rows, "Bewegungsanalyse"

        if key == "depot_ranking":
            raw = q.get_depot_ranking(
                praeparat_ids=praeparat_ids, start_date=start, end_date=end, limit=25
            )
            headers = ["Depot", "Präparat", "Abgaben"]
            rows = [
                [
                    _row_val(r, "depot_name", idx=0),
                    _row_val(r, "praeparat_name", idx=1),
                    _row_val(r, "abgaben_gesamt", idx=2),
                ]
                for r in raw
            ]
            if depot_ids:
                rows = self._filter_rows_by_names(rows, depot_col=0, depot_ids=depot_ids)
            return headers, rows, "Depot-Ranking"

        if key == "praeparat_ranking":
            raw = q.get_praeparat_ranking(
                depot_ids=depot_ids, start_date=start, end_date=end, limit=25
            )
            headers = ["Präparat", "Depot", "Abgaben"]
            rows = [
                [
                    _row_val(r, "praeparat_name", idx=0),
                    _row_val(r, "depot_name", idx=1),
                    _row_val(r, "abgaben_gesamt", idx=2),
                ]
                for r in raw
            ]
            if praeparat_ids:
                rows = self._filter_rows_by_names(rows, praep_col=0, praeparat_ids=praeparat_ids)
            return headers, rows, "Präparat-Ranking"

        if key == "dead_stock":
            raw = q.get_dead_stock(days=max(days, 180))
            headers = ["Präparat", "Depot", "Bestand", "Letzte Bewegung"]
            rows = [
                [
                    _row_val(r, "praeparat_name", idx=0),
                    _row_val(r, "depot_name", idx=1),
                    _row_val(r, "ist_bestand", idx=2),
                    _row_val(r, "letzte_bewegung", idx=3),
                ]
                for r in raw
            ]
            rows = self._filter_rows_by_names(
                rows, depot_col=1, praep_col=0, depot_ids=depot_ids, praeparat_ids=praeparat_ids
            )
            return headers, rows, f"Toter Bestand (>{max(days, 180)} Tage)"

        if key == "turnover":
            raw = q.get_inventory_turnover()
            headers = ["Präparat", "Zugang", "Abgang", "Umschlagsrate"]
            rows = [
                [
                    _row_val(r, "praeparat_name", idx=0),
                    _row_val(r, "zugang", idx=1),
                    _row_val(r, "abgang", idx=2),
                    f"{float(_row_val(r, 'umschlagsrate', 0) or 0):.2f}",
                ]
                for r in raw
            ]
            rows = self._filter_rows_by_names(rows, praep_col=0, praeparat_ids=praeparat_ids)
            return headers, rows, "Lagerumschlag"

        if key == "verfall_forecast":
            months = 12 if days >= 365 else max(3, days // 30)
            raw = q.get_verfall_forecast(months=months)
            headers = ["Monat", "Wert"]
            rows = []
            for r in raw:
                if hasattr(r, "keys"):
                    keys = list(r.keys())
                    a = _row_val(r, keys[0])
                    b = _row_val(r, keys[1]) if len(keys) > 1 else ""
                    rows.append([a, b])
                else:
                    rows.append(list(r)[:2])
            return headers, rows, f"Verfall-Forecast ({months} Monate)"

        return ["Info"], [["Unbekanntes Szenario"]], "Fehler"

    def _fill_table(self, headers: list[str], rows: list) -> None:
        self.result_table.clear()
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                if j >= len(headers):
                    break
                self.result_table.setItem(i, j, QtWidgets.QTableWidgetItem("" if val is None else str(val)))
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setMinimumHeight(min(60 + max(len(rows), 1) * 28, 480))

    def _copy_results(self) -> None:
        if not self._last_headers:
            return
        lines = ["\t".join(self._last_headers)]
        for row in self._last_rows:
            lines.append("\t".join("" if v is None else str(v) for v in row))
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))
        QtWidgets.QMessageBox.information(self, "Kopiert", "Ergebnis in die Zwischenablage kopiert.")
