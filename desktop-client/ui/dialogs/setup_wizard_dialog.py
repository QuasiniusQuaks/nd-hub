# -*- coding: utf-8 -*-
"""Einrichtungswizard: 5 Schritte (Institution, Praeparate, Depots, Kontakt+Zuordnungen, Review), transaktionaler Abschluss."""
from __future__ import annotations

import copy
import json
import logging
from urllib.parse import urlencode, urlparse
from urllib import error as url_error, request as url_request
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from apple_theme import AppleTheme
from core.setup_wizard_contract import (
    DRAFT_VERSION as _DRAFT_VERSION,
    validate_depot_kontakt_and_assignments,
    validate_depot_stamm_rows,
    validate_email_required,
    validate_institution_dict,
    validate_praeparate_names,
)
from db_manager import Database, DB

logger = logging.getLogger("ND-Hub")


def _require_http_scheme(url: str) -> str:
    """Validiert dass die URL nur http/https verwendet (SSRF-Schutz)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url


def _empty_draft() -> Dict[str, Any]:
    return {
        "version": _DRAFT_VERSION,
        "institution": {
            "name": "",
            "strasse": "",
            "hausnummer": "",
            "postleitzahl": "",
            "stadt": "",
            "adresse": "",
            "latitude": None,
            "longitude": None,
        },
        "praeparate": [],
        "depots": [],
    }


def _default_depot_row() -> Dict[str, Any]:
    return {
        "name": "",
        "strasse": "",
        "hausnummer": "",
        "postleitzahl": "",
        "stadt": "",
        "adresse": "",
        "email": "",
        "telefon": "",
        "kontakt_name": "",
        "contacts": [],
        "praeparat_assignments": [],
    }


def _depot_assignments_from_dict(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Liefert normierte Zuordnungen [{name, sollbestand}] aus Entwurfsfeldern (v2/v3)."""
    aa = d.get("praeparat_assignments")
    if isinstance(aa, list) and aa:
        out: List[Dict[str, Any]] = []
        for item in aa:
            if not isinstance(item, dict):
                continue
            n = str(item.get("name") or "").strip()
            if not n:
                continue
            try:
                sb = int(item.get("sollbestand") or 0)
            except (TypeError, ValueError):
                sb = 0
            out.append({"name": n, "sollbestand": max(0, sb)})
        return out
    pnames = d.get("praeparat_names")
    if isinstance(pnames, list):
        return [{"name": str(x).strip(), "sollbestand": 0} for x in pnames if str(x).strip()]
    return []


class SetupWizardDialog(QtWidgets.QDialog):
    """Fuenf-Schritt-Assistent; Schritt 3/4 teilen eine Depot-Oberflaeche (innerer Stack)."""

    _STEP_COUNT = 7

    def __init__(self, parent: Optional[QtWidgets.QWidget], db: Database) -> None:
        super().__init__(parent)
        self.db = db
        self._backdrop: Optional[QtWidgets.QWidget] = None
        self._last_geocode_query: str = ""
        self._last_geocode_result: tuple[Optional[float], Optional[float]] = (None, None)
        self._prae_rows: List[Dict[str, str]] = []
        self.setWindowTitle("Einrichtungswizard")
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(True)
        self.setProperty("embedded_fill_ratio", 0.92)
        self.setProperty("embedded_aspect_ratio", "16:9")
        self.setMinimumSize(980, 720)
        self._resize_for_screen_ratio()
        self._step_index = 0
        self._depot_rows: List[Dict[str, Any]] = []

        c = AppleTheme.current_colors()
        self._apply_base_styles(c)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        self._title = QtWidgets.QLabel("Einrichtungswizard")
        self._title.setStyleSheet(
            f"font-size: 18px; font-weight: 600; color: {c.get('label', '#111')};"
        )
        root.addWidget(self._title)

        self._subtitle = QtWidgets.QLabel(
            "Richten Sie Institution, Präparate, Notfalldepots, Kontakt (E-Mail/Telefon) und Präparat-Zuordnungen ein. "
            "Zwischenstände werden als Entwurf gespeichert; mit „Abschließen“ werden alle Daten in einem Schritt übernommen."
        )
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet(
            f"font-size: 13px; color: {c.get('secondary_label', '#666')};"
        )
        root.addWidget(self._subtitle)

        self._step_label = QtWidgets.QLabel()
        self._step_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {c.get('secondary_label', '#666')};"
        )
        root.addWidget(self._step_label)

        self._stack = QtWidgets.QStackedWidget()
        root.addWidget(self._stack, 1)

        self._page_inst = self._build_institution_page()
        self._page_prae = self._build_praeparate_page()
        self._page_depots = self._build_depots_page()
        self._page_review = self._build_review_page()
        self._page_backend = self._build_backend_page()
        self._stack.addWidget(self._page_backend)
        self._stack.addWidget(self._page_inst)
        self._stack.addWidget(self._page_prae)
        self._stack.addWidget(self._page_depots)
        self._stack.addWidget(self._page_review)

        self._error = QtWidgets.QLabel("")
        self._error.setWordWrap(True)
        self._error.setStyleSheet(f"color: {c.get('red', '#b91c1c')}; font-size: 12px;")
        self._error.hide()
        root.addWidget(self._error)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self._btn_back = QtWidgets.QPushButton("Zurück")
        self._btn_back.setObjectName("btn_secondary")
        self._btn_back.clicked.connect(self._on_back)
        btn_row.addWidget(self._btn_back)

        self._btn_later = QtWidgets.QPushButton("Später")
        self._btn_later.setObjectName("btn_secondary")
        self._btn_later.clicked.connect(self._on_later)
        btn_row.addWidget(self._btn_later)

        self._btn_next = QtWidgets.QPushButton("Weiter")
        self._btn_next.setObjectName("btn_save")
        self._btn_next.clicked.connect(self._on_next)
        btn_row.addWidget(self._btn_next)

        root.addLayout(btn_row)
        self._load_draft_into_ui()

    def _apply_base_styles(self, colors: Dict[str, str]) -> None:
        bg = colors.get("bg_secondary", colors.get("bg_primary", "#f5f5f7"))
        lbl = colors.get("label", "#111")
        inp_bg = colors.get("bg_secondary", "#ffffff")
        sep = colors.get("separator", "#e1e8ed")
        self.setStyleSheet(
            f"QDialog {{ background-color: {bg}; }}"
            f"QDialog QWidget {{ background: transparent; color: {lbl}; }}"
            f"QDialog QLabel {{ background: transparent; color: {lbl}; }}"
            "QDialog QLineEdit, QDialog QPlainTextEdit, QDialog QTableWidget, QDialog QComboBox, QDialog QSpinBox {"
            f"background: {inp_bg};"
            f"color: {lbl};"
            f"border: 2px solid {sep};"
            "min-height: 40px;"
            "padding-top: 4px;"
            "padding-bottom: 4px;"
            "}"
            "QDialog QPushButton {"
            "min-height: 40px;"
            "}"
        )

    def _build_backend_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        hint = QtWidgets.QLabel(
            "Wählen Sie zuerst den Betriebsmodus wie im Sync-Tab. "
            "Bei local_only wird Geokodierung übersprungen."
        )
        hint.setWordWrap(True)
        lay.addWidget(hint)
        form = QtWidgets.QFormLayout()
        self._sync_mode_combo = QtWidgets.QComboBox()
        self._sync_mode_combo.addItem("Nur lokal (local_only)", "local_only")
        self._sync_mode_combo.addItem("Hybrid Sync (hybrid_sync)", "hybrid_sync")
        self._sync_mode_combo.addItem("Nur Remote (remote_only)", "remote_only")
        form.addRow("Betriebsmodus:", self._sync_mode_combo)
        self._sync_backend_url_input = QtWidgets.QLineEdit()
        self._sync_backend_url_input.setPlaceholderText("http://127.0.0.1:8000")
        form.addRow("Backend-URL:", self._sync_backend_url_input)
        self._sync_backend_token_input = QtWidgets.QLineEdit()
        self._sync_backend_token_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self._sync_backend_token_input.setPlaceholderText("Bearer Token aus Web-App")
        form.addRow("Backend-Token:", self._sync_backend_token_input)
        lay.addLayout(form)
        self._sync_mode_combo.currentIndexChanged.connect(self._update_backend_mode_visibility)
        lay.addStretch()
        return w

    def _build_institution_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        form = QtWidgets.QFormLayout()
        form.setSpacing(8)
        self._in_name = QtWidgets.QLineEdit()
        self._in_name.setPlaceholderText("Name der Institution")
        form.addRow("Name:", self._in_name)
        self._in_strasse = QtWidgets.QLineEdit()
        self._in_strasse.setPlaceholderText("Straße")
        form.addRow("Straße:", self._in_strasse)
        self._in_hausnummer = QtWidgets.QLineEdit()
        self._in_hausnummer.setPlaceholderText("Hausnummer")
        form.addRow("Hausnummer:", self._in_hausnummer)
        self._in_plz = QtWidgets.QLineEdit()
        self._in_plz.setPlaceholderText("Postleitzahl")
        form.addRow("Postleitzahl:", self._in_plz)
        self._in_stadt = QtWidgets.QLineEdit()
        self._in_stadt.setPlaceholderText("Stadt")
        form.addRow("Stadt:", self._in_stadt)
        lay.addLayout(form)
        lay.addStretch()
        return w

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

    def _build_review_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QtWidgets.QLabel("Zusammenfassung – bitte prüfen:"))
        self._review_text = QtWidgets.QPlainTextEdit()
        self._review_text.setReadOnly(True)
        self._review_text.setMinimumHeight(260)
        lay.addWidget(self._review_text, 1)
        return w

    def _parse_float_optional(self, raw: str) -> Optional[float]:
        s = (raw or "").strip().replace(",", ".")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def _load_json_draft(self) -> Dict[str, Any]:
        raw = self.db.get_app_setting(DB.SETTING_SETUP_WIZARD_DRAFT, "").strip()
        if not raw:
            return _empty_draft()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("setup_wizard_draft: ungültiges JSON, verwende leeren Entwurf")
            return _empty_draft()
        if not isinstance(data, dict):
            return _empty_draft()
        out = _empty_draft()
        inst = data.get("institution") if isinstance(data.get("institution"), dict) else {}
        out["institution"].update(
            {
                "name": str(inst.get("name") or ""),
                "strasse": str(inst.get("strasse") or ""),
                "hausnummer": str(inst.get("hausnummer") or ""),
                "postleitzahl": str(inst.get("postleitzahl") or ""),
                "stadt": str(inst.get("stadt") or ""),
                "adresse": str(inst.get("adresse") or ""),
                "latitude": inst.get("latitude"),
                "longitude": inst.get("longitude"),
            }
        )
        prs = data.get("praeparate") if isinstance(data.get("praeparate"), list) else []
        for p in prs:
            if isinstance(p, dict) and str(p.get("name") or "").strip():
                out["praeparate"].append(
                    {
                        "name": str(p.get("name") or "").strip(),
                        "wirkstoff": str(p.get("wirkstoff") or "").strip(),
                        "darreichungsform": str(p.get("darreichungsform") or "").strip(),
                        "staerke": str(p.get("staerke") or "").strip(),
                        "einheit": str(p.get("einheit") or "").strip(),
                        "pzn": str(p.get("pzn") or "").strip(),
                        "hersteller": str(p.get("hersteller") or "").strip(),
                    }
                )
        deps = data.get("depots") if isinstance(data.get("depots"), list) else []
        for d in deps:
            if not isinstance(d, dict):
                continue
            row = _default_depot_row()
            row["name"] = str(d.get("name") or "").strip()
            row["strasse"] = str(d.get("strasse") or "").strip()
            row["hausnummer"] = str(d.get("hausnummer") or "").strip()
            row["postleitzahl"] = str(d.get("postleitzahl") or "").strip()
            row["stadt"] = str(d.get("stadt") or "").strip()
            row["adresse"] = str(d.get("adresse") or "").strip()
            row["email"] = str(d.get("email") or "").strip()
            row["telefon"] = str(d.get("telefon") or "").strip()
            row["kontakt_name"] = str(d.get("kontakt_name") or "").strip()
            contacts = d.get("contacts")
            if isinstance(contacts, list):
                row["contacts"] = [c for c in contacts if isinstance(c, dict)]
            row["praeparat_assignments"] = _depot_assignments_from_dict(d)
            out["depots"].append(row)
        return out

    def _prefill_institution_from_db_if_empty(self, draft: Dict[str, Any]) -> None:
        inst = draft.get("institution") or {}
        if str(inst.get("name") or "").strip():
            return
        row = self.db.cur.execute(
            """
            SELECT name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
            FROM institutions ORDER BY id ASC LIMIT 1
            """
        ).fetchone()
        if not row:
            return
        draft["institution"] = {
            "name": str(row[0] or ""),
            "strasse": str(row[2] or "") if row[2] is not None else "",
            "hausnummer": str(row[3] or "") if row[3] is not None else "",
            "postleitzahl": str(row[4] or "") if row[4] is not None else "",
            "stadt": str(row[5] or "") if row[5] is not None else "",
            "adresse": str(row[1] or "") if row[1] is not None else "",
            "latitude": row[6],
            "longitude": row[7],
        }

    def _load_draft_into_ui(self) -> None:
        draft = self._load_json_draft()
        self._prefill_institution_from_db_if_empty(draft)
        self._load_backend_config_into_ui()
        inst = draft.get("institution") or {}
        self._in_name.setText(str(inst.get("name") or ""))
        self._in_strasse.setText(str(inst.get("strasse") or ""))
        self._in_hausnummer.setText(str(inst.get("hausnummer") or ""))
        self._in_plz.setText(str(inst.get("postleitzahl") or ""))
        self._in_stadt.setText(str(inst.get("stadt") or ""))
        self._prae_rows = [p for p in (draft.get("praeparate") or []) if isinstance(p, dict) and str(p.get("name") or "").strip()]
        self._pr_list.clear()
        for p in self._prae_rows:
            self._pr_list.addItem(str(p.get("name") or "").strip())

        self._depot_rows = copy.deepcopy(draft.get("depots") or [])
        if not self._depot_rows:
            self._depot_rows.append(_default_depot_row())
        self._depot_list.blockSignals(True)
        self._depot_list.clear()
        for i, d in enumerate(self._depot_rows):
            label = str(d.get("name") or "").strip() or f"Depot {i + 1}"
            self._depot_list.addItem(label)
        self._depot_list.setCurrentRow(0)
        self._depot_list.blockSignals(False)
        self._depot_list.setProperty("_nd_prev_row", self._depot_list.currentRow())
        self._load_depot_form_from_row(0)
        self._refresh_depot_praeparate_table()

        step_raw = self.db.get_app_setting(DB.SETTING_SETUP_WIZARD_LAST_STEP, "0").strip()
        try:
            self._step_index = max(0, min(self._STEP_COUNT - 1, int(step_raw)))
        except ValueError:
            self._step_index = 0
        if self._step_index == self._STEP_COUNT - 1:
            self._fill_review()
        self._refresh_step_ui()

    def _sync_main_stack_to_step(self) -> None:
        if self._step_index <= 2:
            self._stack.setCurrentIndex(self._step_index)
        elif self._step_index <= 5:
            self._stack.setCurrentIndex(3)
            self._depot_inner_stack.setCurrentIndex(self._step_index - 3)
            self._update_depot_step_hint()
        else:
            self._stack.setCurrentIndex(4)

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

    def _praeparat_names_from_list(self) -> List[str]:
        return [str(p.get("name") or "").strip() for p in self._prae_rows if str(p.get("name") or "").strip()]

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
                contacts: List[Dict[str, str]] = []
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
            assignments: List[Dict[str, Any]] = []
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

    def _load_contacts_for_depot(self, depot_row: Dict[str, Any]) -> None:
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
        assign_map: Dict[str, int] = {}
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

    def _collect_draft(self) -> Dict[str, Any]:
        cur_dep = self._depot_list.currentRow()
        if cur_dep >= 0:
            self._save_depot_form_to_row(cur_dep)

        inst_street = self._in_strasse.text().strip()
        inst_house = self._in_hausnummer.text().strip()
        inst_plz = self._in_plz.text().strip()
        inst_city = self._in_stadt.text().strip()
        inst_address = self._compose_address(inst_street, inst_house, inst_plz, inst_city)
        if self._current_operating_mode() == "local_only":
            lat, lon = None, None
        else:
            lat, lon = self._geocode_address_if_possible(inst_address)
        prs: List[Dict[str, str]] = [dict(p) for p in self._prae_rows if str(p.get("name") or "").strip()]
        depots_out: List[Dict[str, Any]] = []
        for d in self._depot_rows:
            depots_out.append(
                {
                    "name": str(d.get("name") or "").strip(),
                    "strasse": str(d.get("strasse") or "").strip(),
                    "hausnummer": str(d.get("hausnummer") or "").strip(),
                    "postleitzahl": str(d.get("postleitzahl") or "").strip(),
                    "stadt": str(d.get("stadt") or "").strip(),
                    "adresse": str(d.get("adresse") or "").strip(),
                    "email": str(d.get("email") or "").strip(),
                    "telefon": str(d.get("telefon") or "").strip(),
                    "kontakt_name": str(d.get("kontakt_name") or "").strip(),
                    "contacts": list(d.get("contacts") or []),
                    "praeparat_assignments": list(
                        d.get("praeparat_assignments") or []
                    ),
                }
            )
        return {
            "version": _DRAFT_VERSION,
            "institution": {
                "name": self._in_name.text().strip(),
                "strasse": inst_street,
                "hausnummer": inst_house,
                "postleitzahl": inst_plz,
                "stadt": inst_city,
                "adresse": inst_address,
                "latitude": lat,
                "longitude": lon,
            },
            "praeparate": prs,
            "depots": depots_out,
        }

    def _persist_progress(self) -> None:
        draft = self._collect_draft()
        self.db.set_app_setting(DB.SETTING_SETUP_WIZARD_DRAFT, json.dumps(draft, ensure_ascii=False))
        self.db.set_app_setting(DB.SETTING_SETUP_WIZARD_LAST_STEP, str(self._step_index))

    def _fill_review(self) -> None:
        d = self._collect_draft()
        lines: List[str] = []
        lines.append(f"Betriebsmodus: {self._current_operating_mode()}")
        lines.append("")
        inst = d.get("institution") or {}
        lines.append(f"Institution: {inst.get('name')}")
        lines.append(f"  Straße: {inst.get('strasse') or '-'}")
        lines.append(f"  Hausnummer: {inst.get('hausnummer') or '-'}")
        lines.append(f"  Postleitzahl: {inst.get('postleitzahl') or '-'}")
        lines.append(f"  Stadt: {inst.get('stadt') or '-'}")
        lines.append(
            f"  Adresse (zusammengesetzt): {self._compose_address(inst.get('strasse'), inst.get('hausnummer'), inst.get('postleitzahl'), inst.get('stadt')) or inst.get('adresse') or '-'}"
        )
        lines.append(f"  Koordinaten: {inst.get('latitude')}, {inst.get('longitude')}")
        lines.append("")
        lines.append("Präparate:")
        for p in d.get("praeparate") or []:
            if isinstance(p, dict):
                lines.append(f"  - {p.get('name')}")
                detail_parts = []
                for key, label in (
                    ("wirkstoff", "Wirkstoff"),
                    ("darreichungsform", "Darreichungsform"),
                    ("staerke", "Stärke"),
                    ("einheit", "Einheit"),
                    ("pzn", "PZN"),
                    ("hersteller", "Hersteller"),
                ):
                    val = str(p.get(key) or "").strip()
                    if val:
                        detail_parts.append(f"{label}: {val}")
                if detail_parts:
                    lines.append(f"      {' | '.join(detail_parts)}")
                detail_parts = []
                for key, label in (
                    ("wirkstoff", "Wirkstoff"),
                    ("darreichungsform", "Darreichungsform"),
                    ("staerke", "Stärke"),
                    ("einheit", "Einheit"),
                    ("pzn", "PZN"),
                    ("hersteller", "Hersteller"),
                ):
                    val = str(p.get(key) or "").strip()
                    if val:
                        detail_parts.append(f"{label}: {val}")
                if detail_parts:
                    lines.append(f"      {' | '.join(detail_parts)}")
        lines.append("")
        lines.append("Notfalldepots:")
        for dep in d.get("depots") or []:
            if not isinstance(dep, dict):
                continue
            lines.append(f"  - {dep.get('name')}")
            kn = str(dep.get("kontakt_name") or "").strip()
            if kn:
                lines.append(f"      Kontakt-Anzeigename: {kn}")
            lines.append(f"      E-Mail: {dep.get('email')}")
            lines.append(f"      Telefon: {dep.get('telefon') or '-'}")
            contacts = dep.get("contacts") if isinstance(dep.get("contacts"), list) else []
            if contacts:
                lines.append("      Kontakte:")
                for c in contacts:
                    if isinstance(c, dict):
                        lines.append(
                            f"        - {c.get('name') or '-'} | {c.get('rolle') or '-'} | {c.get('telefon') or '-'} | {c.get('email') or '-'}"
                        )
            lines.append(f"      Straße: {dep.get('strasse') or '-'}")
            lines.append(f"      Hausnummer: {dep.get('hausnummer') or '-'}")
            lines.append(f"      Postleitzahl: {dep.get('postleitzahl') or '-'}")
            lines.append(f"      Stadt: {dep.get('stadt') or '-'}")
            lines.append(
                f"      Adresse (zusammengesetzt): {self._compose_address(dep.get('strasse'), dep.get('hausnummer'), dep.get('postleitzahl'), dep.get('stadt')) or dep.get('adresse') or '-'}"
            )
            assigns = _depot_assignments_from_dict(dep)
            if assigns:
                for a in assigns:
                    lines.append(f"      - {a.get('name')} (Soll: {a.get('sollbestand', 0)})")
            else:
                lines.append("      (keine Präparate)")
        self._review_text.setPlainText("\n".join(lines))

    def _refresh_step_ui(self) -> None:
        self._step_label.setText(f"Schritt {self._step_index + 1} von {self._STEP_COUNT}")
        self._btn_back.setEnabled(self._step_index > 0)
        if self._step_index < self._STEP_COUNT - 1:
            self._btn_next.setText("Weiter")
        else:
            self._btn_next.setText("Abschließen")
        self._error.hide()
        self._sync_main_stack_to_step()

    def _show_error(self, msg: str) -> None:
        self._error.setText(msg)
        self._error.show()

    def _validate_institution(self) -> bool:
        inst = {
            "name": self._in_name.text().strip(),
            "adresse": self._compose_address(
                self._in_strasse.text().strip(),
                self._in_hausnummer.text().strip(),
                self._in_plz.text().strip(),
                self._in_stadt.text().strip(),
            ),
        }
        ok, msg = validate_institution_dict(inst)
        if not ok:
            self._show_error(msg)
            return False
        address = self._compose_address(
            self._in_strasse.text().strip(),
            self._in_hausnummer.text().strip(),
            self._in_plz.text().strip(),
            self._in_stadt.text().strip(),
        )
        if not address:
            self._show_error("Bitte Straße, Hausnummer, Postleitzahl und Stadt angeben.")
            return False
        if self._current_operating_mode() != "local_only":
            lat, lon = self._geocode_address_if_possible(address)
            if lat is None or lon is None:
                self._show_error("Automatische Geokodierung fehlgeschlagen. Bitte Backend-Verbindung prüfen.")
                return False
        return True

    def _validate_praeparate(self) -> bool:
        names = self._praeparat_names_from_list()
        ok, msg = validate_praeparate_names(names)
        if not ok:
            self._show_error(msg)
            return False
        return True

    def _on_back(self) -> None:
        self._persist_progress()
        if self._step_index <= 0:
            return
        self._step_index -= 1
        if self._step_index in (3, 4, 5):
            self._update_depot_step_hint()
        if self._step_index == 5:
            self._refresh_depot_praeparate_table()
        self._refresh_step_ui()

    def _on_later(self) -> None:
        self._persist_progress()
        self.reject()

    def _on_next(self) -> None:
        self._error.hide()
        if self._step_index == 0:
            if not self._validate_backend_setup():
                return
            self._persist_backend_config()
            self._persist_progress()
            self._step_index = 1
            self._refresh_step_ui()
            return
        if self._step_index == 1:
            if not self._validate_institution():
                return
            self._persist_progress()
            self._step_index = 2
            self._refresh_step_ui()
            return
        if self._step_index == 2:
            if not self._validate_praeparate():
                return
            self._persist_progress()
            self._step_index = 3
            self._refresh_depot_praeparate_table()
            self._refresh_step_ui()
            return
        if self._step_index == 3:
            cur = self._depot_list.currentRow()
            if cur >= 0:
                self._save_depot_form_to_row(cur)
            ok, msg = validate_depot_stamm_rows(self._depot_rows)
            if not ok:
                self._show_error(msg)
                return
            self._persist_progress()
            self._step_index = 4
            self._refresh_step_ui()
            return
        if self._step_index == 4:
            cur = self._depot_list.currentRow()
            if cur >= 0:
                self._save_depot_form_to_row(cur)
            for d in self._depot_rows:
                contacts = d.get("contacts") if isinstance(d.get("contacts"), list) else []
                if not contacts:
                    self._show_error(f"Notfalldepot '{d.get('name') or '-'}': bitte mindestens einen Kontakt anlegen.")
                    return
                for c in contacts:
                    ok_email, msg_email = validate_email_required(str(c.get("email") or ""))
                    if not ok_email:
                        self._show_error(
                            f"Notfalldepot '{d.get('name') or '-'}': Kontakt '{c.get('name') or '-'}' -> {msg_email}"
                        )
                        return
            self._persist_progress()
            self._step_index = 5
            self._refresh_depot_praeparate_table()
            self._refresh_step_ui()
            return
        if self._step_index == 5:
            cur = self._depot_list.currentRow()
            if cur >= 0:
                self._save_depot_form_to_row(cur)
            pr_set = {n.lower() for n in self._praeparat_names_from_list()}
            ok, msg = validate_depot_kontakt_and_assignments(self._depot_rows, pr_set)
            if not ok:
                self._show_error(msg)
                return
            self._persist_progress()
            self._step_index = 6
            self._fill_review()
            self._refresh_step_ui()
            return
        self._on_finalize()

    def _on_finalize(self) -> None:
        if getattr(self.db, "is_read_only_mode", lambda: False)():
            QtWidgets.QMessageBox.warning(
                self,
                "Nur-Lesen Modus",
                "Die Einrichtung kann im Nur-Lesen Modus nicht abgeschlossen werden.",
            )
            return
        if self.db.count_depots() > 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Einrichtungswizard",
                "Es existieren bereits Notfalldepots in der Datenbank. "
                "Bitte bestehende Daten prüfen oder den Wizard nur bei leerer Depot-Liste verwenden.",
            )
            return
        try:
            draft = self._collect_draft()
            self.db.apply_setup_wizard_draft(draft)
            self.db.set_setup_wizard_completed(True)
            self.db.set_app_setting(DB.SETTING_SETUP_WIZARD_DRAFT, "")
            self.db.set_app_setting(DB.SETTING_SETUP_WIZARD_LAST_STEP, "0")
        except Exception as exc:
            logger.exception("apply_setup_wizard_draft")
            QtWidgets.QMessageBox.critical(
                self,
                "Einrichtung fehlgeschlagen",
                str(exc),
            )
            return
        host = self.parent()
        if isinstance(host, QtWidgets.QWidget) and hasattr(host, "show_toast"):
            getattr(host, "show_toast")("Einrichtung abgeschlossen.", "success")
        self.accept()

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

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self._persist_progress()
        except Exception:
            logger.exception("SetupWizard: persistieren beim Schließen fehlgeschlagen")
        if not (self.windowFlags() & QtCore.Qt.Widget):
            self._hide_backdrop()
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._resize_for_screen_ratio()
        if self.windowFlags() & QtCore.Qt.Widget:
            # Eingebettet im Overlay-Host: Verdunkelung übernimmt der Host.
            return
        self._show_backdrop()
        parent = self.parentWidget()
        if parent is not None:
            geo = parent.geometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _resize_for_screen_ratio(self, ratio: float = 0.92) -> None:
        ratio = min(max(ratio, 0.1), 1.0)
        available_geo: Optional[QtCore.QRect] = None
        parent = self.parentWidget()
        if parent is not None and parent.windowHandle() is not None and parent.windowHandle().screen() is not None:
            available_geo = parent.windowHandle().screen().availableGeometry()
        elif self.windowHandle() is not None and self.windowHandle().screen() is not None:
            available_geo = self.windowHandle().screen().availableGeometry()
        else:
            screen = QtGui.QGuiApplication.primaryScreen()
            if screen is not None:
                available_geo = screen.availableGeometry()
        if available_geo is None:
            return
        max_width = int(available_geo.width() * ratio)
        max_height = int(available_geo.height() * ratio)
        if max_width <= 0 or max_height <= 0:
            return

        # Erzwinge ein breites 16:9-Layout und nutze dabei so viel Platz wie moeglich.
        target_width = max_width
        target_height = int(target_width * 9 / 16)
        if target_height > max_height:
            target_height = max_height
            target_width = int(target_height * 16 / 9)

        target_width = max(self.minimumWidth(), target_width)
        target_height = max(self.minimumHeight(), target_height)
        target_width = min(target_width, available_geo.width())
        target_height = min(target_height, available_geo.height())
        self.resize(target_width, target_height)

    def _show_backdrop(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        if self._backdrop is None:
            self._backdrop = QtWidgets.QWidget(parent)
            self._backdrop.setStyleSheet("background-color: rgba(0, 0, 0, 70);")
            self._backdrop.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self._backdrop.setGeometry(parent.rect())
        self._backdrop.show()
        self._backdrop.raise_()
        self.raise_()

    def _hide_backdrop(self) -> None:
        if self._backdrop is not None:
            self._backdrop.hide()

    def _compose_address(self, street: Any, house: Any, plz: Any, city: Any) -> str:
        street_s = str(street or "").strip()
        house_s = str(house or "").strip()
        plz_s = str(plz or "").strip()
        city_s = str(city or "").strip()
        line1 = " ".join(x for x in [street_s, house_s] if x)
        line2 = " ".join(x for x in [plz_s, city_s] if x)
        return ", ".join(x for x in [line1, line2] if x)

    def _load_backend_config_into_ui(self) -> None:
        host = self.window()
        cfg = getattr(host, "config", None)
        if cfg is None:
            return
        mode = str(getattr(cfg, "get_operating_mode", lambda: "local_only")() or "local_only").strip().lower()
        idx = self._sync_mode_combo.findData(mode)
        self._sync_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._sync_backend_url_input.setText(str(getattr(cfg, "get_backend_url", lambda: "")() or "").strip())
        self._sync_backend_token_input.setText(str(getattr(cfg, "get_backend_token", lambda: "")() or "").strip())
        self._update_backend_mode_visibility()

    def _persist_backend_config(self) -> None:
        host = self.window()
        cfg = getattr(host, "config", None)
        if cfg is None:
            return
        mode = self._current_operating_mode()
        getattr(cfg, "set_operating_mode", lambda _: None)(mode)
        getattr(cfg, "set_backend_url", lambda _: None)(self._sync_backend_url_input.text().strip())
        getattr(cfg, "set_backend_token", lambda _: None)(self._sync_backend_token_input.text().strip())

    def _current_operating_mode(self) -> str:
        return str(self._sync_mode_combo.currentData() or "local_only")

    def _update_backend_mode_visibility(self) -> None:
        local_only = self._current_operating_mode() == "local_only"
        self._sync_backend_url_input.setEnabled(not local_only)
        self._sync_backend_token_input.setEnabled(not local_only)

    def _validate_backend_setup(self) -> bool:
        mode = self._current_operating_mode()
        if mode == "local_only":
            return True
        if not self._sync_backend_url_input.text().strip():
            self._show_error("Bitte Backend-URL für Hybrid/Remote angeben.")
            return False
        return True

    def _geocode_address_if_possible(self, query: str) -> tuple[Optional[float], Optional[float]]:
        q = (query or "").strip()
        if not q:
            return None, None
        if q == self._last_geocode_query:
            return self._last_geocode_result
        host = self.window()
        config = getattr(host, "config", None)
        if config is None:
            return None, None
        base_url = str(getattr(config, "get_backend_url", lambda: "")() or "").strip().rstrip("/")
        if not base_url:
            return None, None
        token = str(getattr(config, "get_backend_token", lambda: "")() or "").strip()
        url = f"{base_url}/geo/geocode?{urlencode({'q': q})}"
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = url_request.Request(_require_http_scheme(url), method="GET", headers=headers)
        try:
            with url_request.urlopen(req, timeout=8.0) as response:  # nosec B310: URL scheme validated by _require_http_scheme
                raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            lat = payload.get("latitude")
            lon = payload.get("longitude")
            try:
                result = (float(lat), float(lon))
                self._last_geocode_query = q
                self._last_geocode_result = result
                return result
            except (TypeError, ValueError):
                return None, None
        except (url_error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return None, None
