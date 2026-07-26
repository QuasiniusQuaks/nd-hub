"""Institution master-data step."""
from __future__ import annotations

from core.setup_wizard_contract import validate_institution_dict
from PySide6 import QtWidgets


class InstitutionStepMixin:
    """Issue #67: institution step extracted from setup_wizard_dialog monolith."""

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


