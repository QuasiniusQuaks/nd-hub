"""Depot step form binding: stamm / kontakte / assignments."""
from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtWidgets


class DepotsFormMixin:
    """Issue #67: depot form load/save extracted from setup_wizard_dialog monolith."""

    def _save_depot_form_to_row(self, row: int) -> None:
        if row < 0 or row >= len(self._depot_rows):
            return
        stamm_only = self._depot_inner_stack.currentIndex() == 0
        if stamm_only:
            prev = dict(self._depot_rows[row])
            prev["name"] = self._d_name.text().strip()
            prev["strasse"] = self._d_strasse.text().strip()
            prev["hausnummer"] = self._d_hausnummer.text().strip()
            prev["postleitzahl"] = self._d_plz.text().strip()
            prev["stadt"] = self._d_stadt.text().strip()
            prev["adresse"] = self._compose_address(
                prev["strasse"], prev["hausnummer"], prev["postleitzahl"], prev["stadt"]
            )
            self._depot_rows[row] = prev
        else:
            if self._depot_inner_stack.currentIndex() == 1:
                contacts: list[dict[str, str]] = []
                for r in range(self._kontakt_table.rowCount()):
                    n = self._kontakt_table.item(r, 0).text().strip() if self._kontakt_table.item(r, 0) else ""
                    ro = self._kontakt_table.item(r, 1).text().strip() if self._kontakt_table.item(r, 1) else ""
                    te = self._kontakt_table.item(r, 2).text().strip() if self._kontakt_table.item(r, 2) else ""
                    em = self._kontakt_table.item(r, 3).text().strip() if self._kontakt_table.item(r, 3) else ""
                    if not em:
                        continue
                    contacts.append({"name": n, "rolle": ro or "Depot", "telefon": te, "email": em})
                prev = dict(self._depot_rows[row])
                prev["contacts"] = contacts
                if contacts:
                    prev["email"] = contacts[0].get("email", "")
                    prev["telefon"] = contacts[0].get("telefon", "")
                    prev["kontakt_name"] = contacts[0].get("name", "")
                self._depot_rows[row] = prev
                label = self._d_name.text().strip() or f"Depot {row + 1}"
                item = self._depot_list.item(row)
                if item is not None:
                    item.setText(label)
                return
            assignments: list[dict[str, Any]] = []
            for r in range(self._depot_pr_table.rowCount()):
                chk = self._depot_pr_table.item(r, 0)
                name_it = self._depot_pr_table.item(r, 1)
                spin = self._depot_pr_table.cellWidget(r, 2)
                if chk is None or name_it is None or not isinstance(spin, QtWidgets.QSpinBox):
                    continue
                if chk.checkState() != QtCore.Qt.Checked:
                    continue
                pname = name_it.text().strip()
                if not pname:
                    continue
                assignments.append({"name": pname, "sollbestand": int(spin.value())})
            prev = dict(self._depot_rows[row])
            prev["name"] = self._d_name.text().strip()
            prev["strasse"] = self._d_strasse.text().strip()
            prev["hausnummer"] = self._d_hausnummer.text().strip()
            prev["postleitzahl"] = self._d_plz.text().strip()
            prev["stadt"] = self._d_stadt.text().strip()
            prev["adresse"] = self._compose_address(
                prev["strasse"], prev["hausnummer"], prev["postleitzahl"], prev["stadt"]
            )
            contacts = prev.get("contacts") if isinstance(prev.get("contacts"), list) else []
            if contacts:
                first = contacts[0] if isinstance(contacts[0], dict) else {}
                prev["email"] = str(first.get("email") or "").strip()
                prev["telefon"] = str(first.get("telefon") or "").strip()
                prev["kontakt_name"] = str(first.get("name") or "").strip()
            else:
                prev["email"] = ""
                prev["telefon"] = ""
                prev["kontakt_name"] = ""
            prev["praeparat_assignments"] = assignments
            self._depot_rows[row] = prev
        label = self._d_name.text().strip() or f"Depot {row + 1}"
        item = self._depot_list.item(row)
        if item is not None:
            item.setText(label)

    def _load_depot_form_from_row(self, row: int) -> None:
        if row < 0 or row >= len(self._depot_rows):
            self._d_name.clear()
            self._d_strasse.clear()
            self._d_hausnummer.clear()
            self._d_plz.clear()
            self._d_stadt.clear()
            self._kontakt_table.setRowCount(0)
            return
        d = self._depot_rows[row]
        self._d_name.setText(str(d.get("name") or ""))
        self._d_strasse.setText(str(d.get("strasse") or ""))
        self._d_hausnummer.setText(str(d.get("hausnummer") or ""))
        self._d_plz.setText(str(d.get("postleitzahl") or ""))
        self._d_stadt.setText(str(d.get("stadt") or ""))
        self._load_contacts_for_depot(d)

    def _load_contacts_for_depot(self, depot_row: dict[str, Any]) -> None:
        contacts = depot_row.get("contacts") if isinstance(depot_row.get("contacts"), list) else []
        if not contacts:
            contacts = [
                {
                    "name": str(depot_row.get("kontakt_name") or depot_row.get("name") or "").strip(),
                    "rolle": "Depot",
                    "telefon": str(depot_row.get("telefon") or "").strip(),
                    "email": str(depot_row.get("email") or "").strip(),
                }
            ]
        self._kontakt_table.setRowCount(0)
        for c in contacts:
            r = self._kontakt_table.rowCount()
            self._kontakt_table.insertRow(r)
            self._kontakt_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(c.get("name") or "")))
            self._kontakt_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(c.get("rolle") or "")))
            self._kontakt_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(c.get("telefon") or "")))
            self._kontakt_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(c.get("email") or "")))

    def _on_depot_pr_table_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        spin = self._depot_pr_table.cellWidget(item.row(), 2)
        if isinstance(spin, QtWidgets.QSpinBox):
            spin.setEnabled(item.checkState() == QtCore.Qt.Checked)

    def _refresh_depot_praeparate_table(self) -> None:
        row = self._depot_list.currentRow()
        if row < 0:
            row = 0
        assign_map: dict[str, int] = {}
        for a in self._depot_rows[row].get("praeparat_assignments") or []:
            if isinstance(a, dict):
                n = str(a.get("name") or "").strip()
                if n:
                    try:
                        sb = int(a.get("sollbestand") or 0)
                    except (TypeError, ValueError):
                        sb = 0
                    assign_map[n.lower()] = max(0, sb)
        pr_names = self._praeparat_names_from_list()
        self._depot_pr_table.blockSignals(True)
        self._depot_pr_table.setRowCount(len(pr_names))
        for r, pname in enumerate(pr_names):
            lk = pname.lower()
            soll = assign_map.get(lk, 0)
            checked = lk in assign_map
            self._depot_pr_table.setRowHeight(r, 56)
            chk = QtWidgets.QTableWidgetItem()
            chk.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chk.setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
            self._depot_pr_table.setItem(r, 0, chk)
            nm = QtWidgets.QTableWidgetItem(pname)
            nm.setFlags(QtCore.Qt.ItemIsEnabled)
            self._depot_pr_table.setItem(r, 1, nm)
            spin = QtWidgets.QSpinBox()
            spin.setRange(0, 999999)
            spin.setValue(soll if checked else 0)
            spin.setEnabled(checked)
            spin.setMinimumWidth(110)
            spin.setFixedHeight(34)
            # Globales QDialog-Stylesheet setzt QSpinBox auf min-height/padding;
            # fuer Tabellenzellen hier kompakt ueberschreiben, damit kein Ueberstand entsteht.
            spin.setStyleSheet(
                "QSpinBox {"
                "min-height: 0px;"
                "padding-top: 0px;"
                "padding-bottom: 0px;"
                "padding-left: 6px;"
                "padding-right: 6px;"
                "margin: 0px;"
                "}"
            )
            self._depot_pr_table.setCellWidget(r, 2, spin)
        self._depot_pr_table.blockSignals(False)


