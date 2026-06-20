"""
Datenvertrag und Feld-Mapping: Desktop-Einrichtungswizard <-> SQLite-Stammdaten.

Hinweis: Praeparate-Stammdaten koennen im Wizard zunaechst schlank (nur `name`) erfasst werden;
Split-Adressfelder fuer Institution und Depots entsprechen dem Server-Modell und werden in SQLite persistiert.
"""
from __future__ import annotations

import re
from typing import Any

DRAFT_VERSION = 3

# --- Wizard JSON (setup_wizard_draft) ---
# institution: { name, adresse, latitude?, longitude? }
# praeparate: [{ name, ... optional extended fields when schema allows }]
# depots: [{
#   name, adresse, email, telefon,
#   kontakt_name?,  # Anzeigename in kontakte.name, sonst Depotname
#   praeparat_assignments: [{ name, sollbestand }]
# }]

# --- Mapping Desktop-SQLite (Ist-Stand) ---
MAPPING_INSTITUTION = {
    "wizard.institution.name": ("institutions", "name", True),
    "wizard.institution.adresse": ("institutions", "adresse", False),
    "wizard.institution.latitude": ("institutions", "latitude", False),
    "wizard.institution.longitude": ("institutions", "longitude", False),
}

MAPPING_PRAEPARAT = {
    "wizard.praeparate[].name": ("praeparate", "name", True),
}

MAPPING_DEPOT = {
    "wizard.depots[].name": ("depots", "name", True),
    "wizard.depots[].adresse": ("depots", "adresse", False),
    "wizard.depots[].email": ("depots", "email", True),
    "wizard.depots[].telefon": ("depots", "telefon", False),
    "wizard.depots[].institution_id": ("depots", "institution_id", True),
}

MAPPING_KONTAKT = {
    "wizard.depots[].kontakt_name": ("kontakte", "name", False),
    "wizard.depots[].email": ("kontakte", "email", True),
    "wizard.depots[].telefon": ("kontakte", "telefon", False),
    "kontakte.rolle": ("kontakte", "rolle", True),  # fest "Depot"
}

MAPPING_DEPOT_PRAEPARAT = {
    "wizard.depots[].praeparat_assignments[].name": ("depot_praeparate", "praeparat_id", True),
    "wizard.depots[].praeparat_assignments[].sollbestand": ("depot_praeparate", "sollbestand", True),
}

_PLZ_RE = re.compile(r"^\d{5}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_postleitzahl_optional(value: str) -> tuple[bool, str]:
    """Wenn gesetzt, muss PLZ exakt 5 Ziffern sein (für zukuenftige Schema-Felder)."""
    s = (value or "").strip()
    if not s:
        return True, ""
    if not _PLZ_RE.match(s):
        return False, "Postleitzahl muss genau 5 Ziffern haben."
    return True, ""


def validate_email_required(value: str) -> tuple[bool, str]:
    s = (value or "").strip()
    if not s:
        return False, "E-Mail ist Pflicht."
    if not _EMAIL_RE.match(s):
        return False, "E-Mail-Format ungueltig."
    return True, ""


def validate_institution_dict(inst: dict[str, Any]) -> tuple[bool, str]:
    name = str(inst.get("name") or "").strip()
    if not name:
        return False, "Institutionsname fehlt."
    return True, ""


def validate_praeparate_names(names: list[str]) -> tuple[bool, str]:
    cleaned = [n.strip() for n in names if n and str(n).strip()]
    if not cleaned:
        return False, "Mindestens ein Praeparat."
    lower = [n.lower() for n in cleaned]
    if len(lower) != len(set(lower)):
        return False, "Praeparatnamen duerfen sich nicht wiederholen."
    return True, ""


def validate_depot_stamm_rows(rows: list[dict[str, Any]]) -> tuple[bool, str]:
    if not rows:
        return False, "Mindestens ein Notfalldepot."
    for d in rows:
        nm = str(d.get("name") or "").strip()
        if not nm:
            return False, "Jedes Depot braucht einen Namen."
    return True, ""


def validate_depot_kontakt_and_assignments(
    rows: list[dict[str, Any]],
    prae_names_lower: set[str],
) -> tuple[bool, str]:
    for d in rows:
        nm = str(d.get("name") or "").strip()
        em = str(d.get("email") or "").strip()
        ok, msg = validate_email_required(em)
        if not ok:
            return False, f"Depot '{nm}': {msg}"
        assigns = d.get("praeparat_assignments")
        if not isinstance(assigns, list) or not assigns:
            return False, f"Depot '{nm}': mindestens ein Praeparat zuordnen."
        seen: set[str] = set()
        for a in assigns:
            if not isinstance(a, dict):
                continue
            pn = str(a.get("name") or "").strip()
            if not pn:
                continue
            lk = pn.lower()
            if lk in seen:
                return False, f"Depot '{nm}': Praeparat '{pn}' doppelt."
            seen.add(lk)
            if lk not in prae_names_lower:
                return False, f"Depot '{nm}': Praeparat '{pn}' unbekannt."
            try:
                sb = int(a.get("sollbestand") or 0)
            except (TypeError, ValueError):
                return False, f"Depot '{nm}': ungueltiger Sollbestand fuer '{pn}'."
            if sb < 0:
                return False, f"Depot '{nm}': Sollbestand fuer '{pn}' muss >= 0 sein."
    return True, ""
