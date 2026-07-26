"""Draft load/collect/persist and geocoding helpers."""
from __future__ import annotations

import copy
import json
import logging
from typing import Any
from urllib import error as url_error
from urllib import request as url_request
from urllib.parse import urlencode

from core.setup_wizard_contract import DRAFT_VERSION as _DRAFT_VERSION
from db_manager import DB

from ui.dialogs.setup_wizard.helpers import (
    _default_depot_row,
    _depot_assignments_from_dict,
    _empty_draft,
    _require_http_scheme,
)

logger = logging.getLogger("ND-Hub")


class DraftMixin:
    """Issue #67: draft persistence + geocode extracted from setup_wizard_dialog monolith."""

    def _parse_float_optional(self, raw: str) -> float | None:
        s = (raw or "").strip().replace(",", ".")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def _load_json_draft(self) -> dict[str, Any]:
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

    def _prefill_institution_from_db_if_empty(self, draft: dict[str, Any]) -> None:
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

    def _collect_draft(self) -> dict[str, Any]:
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
        prs: list[dict[str, str]] = [dict(p) for p in self._prae_rows if str(p.get("name") or "").strip()]
        depots_out: list[dict[str, Any]] = []
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

    def _compose_address(self, street: Any, house: Any, plz: Any, city: Any) -> str:
        street_s = str(street or "").strip()
        house_s = str(house or "").strip()
        plz_s = str(plz or "").strip()
        city_s = str(city or "").strip()
        line1 = " ".join(x for x in [street_s, house_s] if x)
        line2 = " ".join(x for x in [plz_s, city_s] if x)
        return ", ".join(x for x in [line1, line2] if x)

    def _geocode_address_if_possible(self, query: str) -> tuple[float | None, float | None]:
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

