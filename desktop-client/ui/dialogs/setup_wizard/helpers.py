"""Pure helpers for the setup wizard (no Qt state)."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from core.setup_wizard_contract import DRAFT_VERSION as _DRAFT_VERSION


def _require_http_scheme(url: str) -> str:
    """Validiert dass die URL nur http/https verwendet (SSRF-Schutz)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url


def _empty_draft() -> dict[str, Any]:
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


def _default_depot_row() -> dict[str, Any]:
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


def _depot_assignments_from_dict(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Liefert normierte Zuordnungen [{name, sollbestand}] aus Entwurfsfeldern (v2/v3)."""
    aa = d.get("praeparat_assignments")
    if isinstance(aa, list) and aa:
        out: list[dict[str, Any]] = []
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


