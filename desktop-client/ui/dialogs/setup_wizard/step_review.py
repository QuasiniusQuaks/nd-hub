"""Review / summary step."""
from __future__ import annotations

from PySide6 import QtWidgets

from ui.dialogs.setup_wizard.helpers import _depot_assignments_from_dict


class ReviewStepMixin:
    """Issue #67: review step extracted from setup_wizard_dialog monolith."""

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

    def _fill_review(self) -> None:
        d = self._collect_draft()
        lines: list[str] = []
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


