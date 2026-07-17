"""Praeparate step."""
from __future__ import annotations

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from core.setup_wizard_contract import validate_praeparate_names


class PraeparateStepMixin:
    """Issue #67: praeparate step extracted from setup_wizard_dialog monolith."""

    def _build_praeparate_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        hint = QtWidgets.QLabel(
            "Mindestens ein Präparat. Bitte alle hinterlegbaren Präparate-Felder ausfüllen."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: {AppleTheme.current_colors().get('secondary_label', '#666')}; font-size: 12px;"
        )
        lay.addWidget(hint)
        row = QtWidgets.QHBoxLayout()
        self._pr_in = QtWidgets.QLineEdit()
        self._pr_in.setPlaceholderText("Präparatname")
        row.addWidget(self._pr_in, 1)
        btn_add = QtWidgets.QPushButton("Hinzufügen")
        btn_add.setObjectName("btn_secondary")
        btn_add.clicked.connect(self._add_praeparat_row)
        row.addWidget(btn_add)
        lay.addLayout(row)
        self._pr_wirkstoff = QtWidgets.QLineEdit()
        self._pr_wirkstoff.setPlaceholderText("Wirkstoff")
        lay.addWidget(self._pr_wirkstoff)
        self._pr_darreichungsform = QtWidgets.QLineEdit()
        self._pr_darreichungsform.setPlaceholderText("Darreichungsform")
        lay.addWidget(self._pr_darreichungsform)
        self._pr_staerke = QtWidgets.QLineEdit()
        self._pr_staerke.setPlaceholderText("Stärke")
        lay.addWidget(self._pr_staerke)
        self._pr_einheit = QtWidgets.QLineEdit()
        self._pr_einheit.setPlaceholderText("Einheit")
        lay.addWidget(self._pr_einheit)
        self._pr_pzn = QtWidgets.QLineEdit()
        self._pr_pzn.setPlaceholderText("PZN")
        lay.addWidget(self._pr_pzn)
        self._pr_hersteller = QtWidgets.QLineEdit()
        self._pr_hersteller.setPlaceholderText("Hersteller")
        lay.addWidget(self._pr_hersteller)
        self._pr_list = QtWidgets.QListWidget()
        self._pr_list.setMinimumHeight(200)
        lay.addWidget(self._pr_list, 1)
        rm = QtWidgets.QPushButton("Markiertes entfernen")
        rm.setObjectName("btn_delete")
        rm.clicked.connect(self._remove_selected_praeparat)
        lay.addWidget(rm)
        return w

    def _validate_praeparate(self) -> bool:
        names = self._praeparat_names_from_list()
        ok, msg = validate_praeparate_names(names)
        if not ok:
            self._show_error(msg)
            return False
        return True

    def _add_praeparat_row(self) -> None:
        n = self._pr_in.text().strip()
        if not n:
            return
        entry = {
            "name": n,
            "wirkstoff": self._pr_wirkstoff.text().strip(),
            "darreichungsform": self._pr_darreichungsform.text().strip(),
            "staerke": self._pr_staerke.text().strip(),
            "einheit": self._pr_einheit.text().strip(),
            "pzn": self._pr_pzn.text().strip(),
            "hersteller": self._pr_hersteller.text().strip(),
        }
        self._prae_rows.append(entry)
        self._pr_list.addItem(n)
        self._pr_in.clear()
        self._pr_wirkstoff.clear()
        self._pr_darreichungsform.clear()
        self._pr_staerke.clear()
        self._pr_einheit.clear()
        self._pr_pzn.clear()
        self._pr_hersteller.clear()
        self._pr_in.setFocus()
        if self._step_index >= 3:
            self._refresh_depot_praeparate_table()

    def _remove_selected_praeparat(self) -> None:
        row = self._pr_list.currentRow()
        if row >= 0:
            self._pr_list.takeItem(row)
            if row < len(self._prae_rows):
                self._prae_rows.pop(row)
        if self._step_index >= 3:
            self._refresh_depot_praeparate_table()

    def _praeparat_names_from_list(self) -> list[str]:
        return [str(p.get("name") or "").strip() for p in self._prae_rows if str(p.get("name") or "").strip()]


