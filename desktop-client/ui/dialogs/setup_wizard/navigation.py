"""Wizard navigation and finalize."""
from __future__ import annotations

import logging

from PySide6 import QtWidgets

from core.setup_wizard_contract import (
    validate_depot_kontakt_and_assignments,
    validate_depot_stamm_rows,
    validate_email_required,
)
from db_manager import DB

logger = logging.getLogger("ND-Hub")


class NavigationMixin:
    """Issue #67: next/back/later/finalize extracted from setup_wizard_dialog monolith."""

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
            host.show_toast("Einrichtung abgeschlossen.", "success")
        self.accept()


