"""Depot step UI: list + multi-substep container."""
from __future__ import annotations

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from ui.dialogs.setup_wizard.helpers import _default_depot_row


class DepotsStepMixin:
    """Issue #67: depot multi-substep UI (list + shell)."""

    def _build_depots_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._depot_hint = QtWidgets.QLabel()
        self._depot_hint.setWordWrap(True)
        self._depot_hint.setStyleSheet(
            f"color: {AppleTheme.current_colors().get('secondary_label', '#666')}; font-size: 12px;"
        )
        lay.addWidget(self._depot_hint)

        split = QtWidgets.QHBoxLayout()
        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("Depots:"))
        self._depot_list = QtWidgets.QListWidget()
        self._depot_list.setMinimumWidth(240)
        self._depot_list.currentRowChanged.connect(self._on_depot_row_changed)
        left.addWidget(self._depot_list)
        row_btns = QtWidgets.QHBoxLayout()
        b_add = QtWidgets.QPushButton("Depot hinzufügen")
        b_add.setObjectName("btn_secondary")
        b_add.clicked.connect(self._add_depot_row)
        b_rm = QtWidgets.QPushButton("Entfernen")
        b_rm.setObjectName("btn_delete")
        b_rm.clicked.connect(self._remove_depot_row)
        row_btns.addWidget(b_add)
        row_btns.addWidget(b_rm)
        left.addLayout(row_btns)
        split.addLayout(left)

        right_outer = QtWidgets.QVBoxLayout()
        self._depot_inner_stack = QtWidgets.QStackedWidget()

        stamm = QtWidgets.QWidget()
        st_l = QtWidgets.QVBoxLayout(stamm)
        st_l.setContentsMargins(0, 0, 0, 0)
        form_st = QtWidgets.QFormLayout()
        self._d_name = QtWidgets.QLineEdit()
        self._d_name.setPlaceholderText("Name Notfalldepot")
        form_st.addRow("Name:", self._d_name)
        self._d_strasse = QtWidgets.QLineEdit()
        self._d_strasse.setPlaceholderText("Straße")
        form_st.addRow("Straße:", self._d_strasse)
        self._d_hausnummer = QtWidgets.QLineEdit()
        self._d_hausnummer.setPlaceholderText("Hausnummer")
        form_st.addRow("Hausnummer:", self._d_hausnummer)
        self._d_plz = QtWidgets.QLineEdit()
        self._d_plz.setPlaceholderText("Postleitzahl")
        form_st.addRow("Postleitzahl:", self._d_plz)
        self._d_stadt = QtWidgets.QLineEdit()
        self._d_stadt.setPlaceholderText("Stadt")
        form_st.addRow("Stadt:", self._d_stadt)
        st_l.addLayout(form_st)
        st_l.addStretch()
        self._depot_inner_stack.addWidget(stamm)

        kont = QtWidgets.QWidget()
        ko_l = QtWidgets.QVBoxLayout(kont)
        ko_l.setContentsMargins(0, 0, 0, 0)
        self._d_kontakt_context = QtWidgets.QLabel("")
        self._d_kontakt_context.setStyleSheet(
            f"font-weight: 600; color: {AppleTheme.current_colors().get('label', '#111')};"
        )
        ko_l.addWidget(self._d_kontakt_context)
        self._kontakt_table = QtWidgets.QTableWidget(0, 4)
        self._kontakt_table.setHorizontalHeaderLabels(["Name", "Rolle", "Telefon", "E-Mail"])
        k_header = self._kontakt_table.horizontalHeader()
        k_header.setStretchLastSection(False)
        k_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        k_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        k_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        k_header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self._kontakt_table.setColumnWidth(0, 180)
        self._kontakt_table.setColumnWidth(1, 170)
        self._kontakt_table.setColumnWidth(2, 160)
        self._kontakt_table.verticalHeader().setDefaultSectionSize(38)
        self._kontakt_table.setMinimumHeight(160)
        ko_l.addWidget(self._kontakt_table, 1)
        kontakt_btns = QtWidgets.QHBoxLayout()
        self._btn_contact_add = QtWidgets.QPushButton("Kontakt hinzufügen")
        self._btn_contact_add.setObjectName("btn_secondary")
        self._btn_contact_add.clicked.connect(self._add_contact_row)
        self._btn_contact_remove = QtWidgets.QPushButton("Kontakt entfernen")
        self._btn_contact_remove.setObjectName("btn_delete")
        self._btn_contact_remove.clicked.connect(self._remove_contact_row)
        kontakt_btns.addWidget(self._btn_contact_add)
        kontakt_btns.addWidget(self._btn_contact_remove)
        kontakt_btns.addStretch()
        ko_l.addLayout(kontakt_btns)
        self._depot_inner_stack.addWidget(kont)

        assign = QtWidgets.QWidget()
        as_l = QtWidgets.QVBoxLayout(assign)
        as_l.setContentsMargins(0, 0, 0, 0)
        as_l.addWidget(QtWidgets.QLabel("Präparate zuordnen (Sollbestand):"))
        self._depot_pr_table = QtWidgets.QTableWidget(0, 3)
        self._depot_pr_table.setHorizontalHeaderLabels(["", "Präparat", "Sollbestand"])
        pr_header = self._depot_pr_table.horizontalHeader()
        pr_header.setStretchLastSection(False)
        pr_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        pr_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        pr_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        # Zeilenhöhe explizit größer, damit Sollbestand-SpinBox sauber in der Zeile sitzt.
        self._depot_pr_table.verticalHeader().setDefaultSectionSize(56)
        self._depot_pr_table.setColumnWidth(0, 44)
        self._depot_pr_table.setColumnWidth(2, 140)
        self._depot_pr_table.setMinimumHeight(180)
        self._depot_pr_table.itemChanged.connect(self._on_depot_pr_table_item_changed)
        as_l.addWidget(self._depot_pr_table, 1)
        self._depot_inner_stack.addWidget(assign)

        right_outer.addWidget(self._depot_inner_stack, 1)
        split.addLayout(right_outer, 1)
        lay.addLayout(split, 1)
        return w

    def _update_depot_step_hint(self) -> None:
        if self._step_index == 3:
            self._depot_hint.setText(
                "Schritt 4 von 7: Stammdaten je Notfalldepot (Name, Adresse). "
                "Mehrere Depots über die Liste links."
            )
        elif self._step_index == 4:
            self._depot_hint.setText(
                "Schritt 5 von 7: Kontakte je Notfalldepot (Name, Rolle, Telefon, E-Mail)."
            )
        elif self._step_index == 5:
            self._depot_hint.setText(
                "Schritt 6 von 7: Präparat-Zuordnungen mit Sollbestand."
            )
        row = self._depot_list.currentRow()
        if row >= 0 and row < len(self._depot_rows):
            dn = str(self._depot_rows[row].get("name") or "").strip() or f"Depot {row + 1}"
            self._d_kontakt_context.setText(f"Aktuelles Depot: {dn}")
        else:
            self._d_kontakt_context.setText("")

    def _add_depot_row(self) -> None:
        cur = self._depot_list.currentRow()
        if cur >= 0:
            self._save_depot_form_to_row(cur)
        self._depot_rows.append(_default_depot_row())
        self._depot_list.addItem(f"Depot {len(self._depot_rows)}")
        self._depot_list.setCurrentRow(len(self._depot_rows) - 1)

    def _remove_depot_row(self) -> None:
        if len(self._depot_rows) <= 1:
            QtWidgets.QMessageBox.information(
                self, "Depots", "Mindestens ein Depot muss erhalten bleiben."
            )
            return
        row = self._depot_list.currentRow()
        if row < 0:
            return
        self._depot_rows.pop(row)
        self._depot_list.takeItem(row)
        if self._depot_list.count() > 0:
            self._depot_list.setCurrentRow(min(row, self._depot_list.count() - 1))
        self._on_depot_row_changed(self._depot_list.currentRow())


    def _on_depot_row_changed(self, row: int) -> None:
        prev = self._depot_list.property("_nd_prev_row")
        if prev is not None:
            try:
                pi = int(prev)
                if pi >= 0:
                    self._save_depot_form_to_row(pi)
            except (TypeError, ValueError):
                pass
        self._depot_list.setProperty("_nd_prev_row", row if row >= 0 else None)
        if row >= 0:
            self._load_depot_form_from_row(row)
            self._refresh_depot_praeparate_table()

    def _add_contact_row(self) -> None:
        r = self._kontakt_table.rowCount()
        self._kontakt_table.insertRow(r)
        self._kontakt_table.setItem(r, 0, QtWidgets.QTableWidgetItem(""))
        self._kontakt_table.setItem(r, 1, QtWidgets.QTableWidgetItem("Depot"))
        self._kontakt_table.setItem(r, 2, QtWidgets.QTableWidgetItem(""))
        self._kontakt_table.setItem(r, 3, QtWidgets.QTableWidgetItem(""))

    def _remove_contact_row(self) -> None:
        r = self._kontakt_table.currentRow()
        if r >= 0:
            self._kontakt_table.removeRow(r)


