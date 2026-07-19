"""Setup-Wizard und App-Settings (Issue #66 Phase 3).

LOC-Split aus ``db_manager.Database``.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

from core.db.constants import DB
from core.db.helpers import _coerce_opt_float

logger = logging.getLogger(__name__)


class SetupWizardMixin:
    """App-Settings, Counts und Setup-Wizard-Apply. Issue #66 Phase 3.

    Erwartet: ``self.cur``, ``self.conn``, ``enqueue_sync_change``,
    ``_clear_lookup_caches``.
    """

    def get_app_setting(self, key: str, default: str = "") -> str:
        try:
            row = self.cur.execute(
                "SELECT wert FROM einstellungen WHERE schluessel = ?",
                (key,),
            ).fetchone()
            if row is None or row[0] is None:
                return default
            return str(row[0])
        except sqlite3.Error:
            return default

    def set_app_setting(self, key: str, value: str):
        self.cur.execute(
            "INSERT OR REPLACE INTO einstellungen (schluessel, wert) VALUES (?, ?)",
            (key, str(value) if value is not None else ""),
        )
        self.conn.commit()

    def count_praeparate(self) -> int:
        row = self.cur.execute("SELECT COUNT(*) FROM praeparate").fetchone()
        return int(row[0]) if row else 0

    def count_depots(self) -> int:
        row = self.cur.execute("SELECT COUNT(*) FROM depots").fetchone()
        return int(row[0]) if row else 0

    def is_setup_wizard_completed(self) -> bool:
        raw = self.get_app_setting(DB.SETTING_SETUP_WIZARD_COMPLETED, "0").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def set_setup_wizard_completed(self, completed: bool) -> None:
        self.set_app_setting(DB.SETTING_SETUP_WIZARD_COMPLETED, "1" if completed else "0")

    def needs_setup_wizard(self) -> bool:
        """True, wenn Ersteinrichtung noch sinnvoll ist (keine Stammdaten oder Wizard nicht abgeschlossen)."""
        if self.is_setup_wizard_completed():
            return False
        return self.count_praeparate() == 0 or self.count_depots() == 0

    def apply_setup_wizard_draft(self, draft: dict[str, Any]) -> None:
        """
        Schreibt Institution, Präparate, Depots, depot_praeparate und einen Depot-Kontakt
        (Tabelle kontakte) in einer Transaktion. Outbox-Einträge erfolgen erst nach COMMIT.

        Voraussetzung: Es dürfen noch keine Depots existieren (sonst RuntimeError).
        Präparate werden bei Bedarf ergänzt (Namensabgleich case-insensitive).
        """
        if self.count_depots() > 0:
            raise RuntimeError("Es existieren bereits Notfalldepots. Einrichtungswizard kann nicht angewendet werden.")

        inst = draft.get("institution") if isinstance(draft.get("institution"), dict) else {}
        prs = draft.get("praeparate") if isinstance(draft.get("praeparate"), list) else []
        deps = draft.get("depots") if isinstance(draft.get("depots"), list) else []

        inst_name = str(inst.get("name") or "").strip()
        if not inst_name:
            raise RuntimeError("Institutionsname fehlt.")

        new_praeparat_ids: list[int] = []
        new_depot_ids: list[int] = []
        new_kontakt_ids: list[int] = []
        new_dp_keys: list[tuple[int, int, int]] = []

        try:
            self.cur.execute("BEGIN")
            row = self.cur.execute("SELECT id FROM institutions ORDER BY id ASC LIMIT 1").fetchone()
            if not row:
                raise RuntimeError("Keine Institution in der Datenbank.")
            inst_id = int(row[0])
            i_str = str(inst.get("strasse") or "").strip() or None
            i_hnr = str(inst.get("hausnummer") or "").strip() or None
            i_plz = str(inst.get("postleitzahl") or "").strip() or None
            i_stadt = str(inst.get("stadt") or "").strip() or None
            self.cur.execute(
                """
                UPDATE institutions
                SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?,
                    latitude = ?, longitude = ?
                WHERE id = ?
                """,
                (
                    inst_name,
                    (str(inst.get("adresse") or "").strip() or None),
                    i_str,
                    i_hnr,
                    i_plz,
                    i_stadt,
                    _coerce_opt_float(inst.get("latitude")),
                    _coerce_opt_float(inst.get("longitude")),
                    inst_id,
                ),
            )

            name_to_id: dict[str, int] = {}
            for p in prs:
                if not isinstance(p, dict):
                    continue
                pname = str(p.get("name") or "").strip()
                if not pname:
                    continue
                key = pname.lower()
                ex = self.cur.execute(
                    "SELECT id FROM praeparate WHERE lower(name) = lower(?)",
                    (pname,),
                ).fetchone()
                if ex:
                    name_to_id[key] = int(ex[0])
                else:
                    self.cur.execute(
                        """
                        INSERT INTO praeparate
                            (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pname,
                            str(p.get("wirkstoff") or "").strip() or None,
                            str(p.get("darreichungsform") or "").strip() or None,
                            str(p.get("staerke") or "").strip() or None,
                            str(p.get("einheit") or "").strip() or None,
                            str(p.get("pzn") or "").strip() or None,
                            str(p.get("hersteller") or "").strip() or None,
                        ),
                    )
                    pid = int(self.cur.lastrowid)
                    name_to_id[key] = pid
                    new_praeparat_ids.append(pid)

            for d in deps:
                if not isinstance(d, dict):
                    continue
                d_name = str(d.get("name") or "").strip()
                contacts = d.get("contacts") if isinstance(d.get("contacts"), list) else []
                first_contact_email = ""
                first_contact_phone = ""
                if contacts:
                    first = contacts[0] if isinstance(contacts[0], dict) else {}
                    first_contact_email = str(first.get("email") or "").strip()
                    first_contact_phone = str(first.get("telefon") or "").strip()
                d_email = str(d.get("email") or "").strip() or first_contact_email
                if not d_name or not d_email:
                    raise RuntimeError("Jedes Notfalldepot braucht Name und mindestens einen Kontakt mit E-Mail.")
                d_adr = str(d.get("adresse") or "").strip() or None
                d_tel = str(d.get("telefon") or "").strip() or first_contact_phone or None
                d_str = str(d.get("strasse") or "").strip() or None
                d_hnr = str(d.get("hausnummer") or "").strip() or None
                d_plz = str(d.get("postleitzahl") or "").strip() or None
                d_stadt = str(d.get("stadt") or "").strip() or None
                d_lat = _coerce_opt_float(d.get("latitude"))
                d_lon = _coerce_opt_float(d.get("longitude"))
                self.cur.execute(
                    """
                    INSERT INTO depots (
                        name, adresse, telefon, email, institution_id,
                        strasse, hausnummer, postleitzahl, stadt, latitude, longitude
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d_name,
                        d_adr,
                        d_tel,
                        d_email,
                        inst_id,
                        d_str,
                        d_hnr,
                        d_plz,
                        d_stadt,
                        d_lat,
                        d_lon,
                    ),
                )
                depot_id = int(self.cur.lastrowid)
                new_depot_ids.append(depot_id)

                if contacts:
                    for c in contacts:
                        if not isinstance(c, dict):
                            continue
                        cname = str(c.get("name") or "").strip() or d_name
                        crole = str(c.get("rolle") or "").strip() or "Depot"
                        ctel = str(c.get("telefon") or "").strip() or None
                        cemail = str(c.get("email") or "").strip()
                        if not cemail:
                            continue
                        self.cur.execute(
                            """
                            INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (depot_id, cname, crole, ctel, cemail),
                        )
                        new_kontakt_ids.append(int(self.cur.lastrowid))
                else:
                    kontakt_display = str(d.get("kontakt_name") or "").strip() or d_name
                    self.cur.execute(
                        """
                        INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (depot_id, kontakt_display, "Depot", d_tel, d_email),
                    )
                    new_kontakt_ids.append(int(self.cur.lastrowid))

                assignments = d.get("praeparat_assignments")
                rows_to_insert: list[tuple[str, int]] = []
                if isinstance(assignments, list) and assignments:
                    seen_a: set[str] = set()
                    for item in assignments:
                        if not isinstance(item, dict):
                            continue
                        pn = str(item.get("name") or "").strip()
                        if not pn:
                            continue
                        lk = pn.lower()
                        if lk in seen_a:
                            continue
                        seen_a.add(lk)
                        try:
                            soll = int(item.get("sollbestand") or 0)
                        except (TypeError, ValueError):
                            soll = 0
                        rows_to_insert.append((pn, max(0, soll)))
                else:
                    pnames = d.get("praeparat_names") if isinstance(d.get("praeparat_names"), list) else []
                    for raw in pnames:
                        pn = str(raw or "").strip()
                        if pn:
                            rows_to_insert.append((pn, 0))
                if not rows_to_insert:
                    raise RuntimeError(f"Notfalldepot '{d_name}': Bitte mindestens ein Präparat zuordnen.")
                for pn, soll in rows_to_insert:
                    lk = pn.lower()
                    pid = name_to_id.get(lk)
                    if pid is None:
                        raise RuntimeError(
                            f"Notfalldepot '{d_name}': Präparat '{pn}' ist nicht in der Wizard-Liste."
                        )
                    self.cur.execute(
                        """
                        INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                        VALUES (?, ?, ?)
                        """,
                        (depot_id, pid, soll),
                    )
                    new_dp_keys.append((depot_id, pid, soll))

            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        self._clear_lookup_caches()

        inst_row = self.cur.execute(
            """
            SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
            FROM institutions WHERE id = ?
            """,
            (inst_id,),
        ).fetchone()
        if inst_row:
            self.enqueue_sync_change(
                "institutions",
                "update",
                {
                    "id": int(inst_row[0]),
                    "name": inst_row[1],
                    "adresse": inst_row[2],
                    "strasse": inst_row[3],
                    "hausnummer": inst_row[4],
                    "postleitzahl": inst_row[5],
                    "stadt": inst_row[6],
                    "latitude": inst_row[7],
                    "longitude": inst_row[8],
                },
                dedupe_key=f"wizard:institutions:update:{inst_id}",
            )

        for pid in new_praeparat_ids:
            nm_row = self.cur.execute(
                """
                SELECT name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
                FROM praeparate WHERE id = ?
                """,
                (pid,),
            ).fetchone()
            nm = str(nm_row[0]) if nm_row else ""
            self.enqueue_sync_change(
                "praeparate",
                "create",
                {
                    "id": int(pid),
                    "name": nm,
                    "wirkstoff": nm_row[1] if nm_row else None,
                    "darreichungsform": nm_row[2] if nm_row else None,
                    "staerke": nm_row[3] if nm_row else None,
                    "einheit": nm_row[4] if nm_row else None,
                    "pzn": nm_row[5] if nm_row else None,
                    "hersteller": nm_row[6] if nm_row else None,
                },
                dedupe_key=f"wizard:praeparate:create:{pid}",
            )
        for did in new_depot_ids:
            r = self.cur.execute(
                """
                SELECT name, adresse, telefon, email, institution_id, strasse, hausnummer, postleitzahl, stadt,
                       latitude, longitude
                FROM depots WHERE id = ?
                """,
                (did,),
            ).fetchone()
            if r:
                self.enqueue_sync_change(
                    "depots",
                    "create",
                    {
                        "id": int(did),
                        "name": r[0],
                        "adresse": r[1],
                        "telefon": r[2],
                        "email": r[3],
                        "institution_id": r[4],
                        "strasse": r[5],
                        "hausnummer": r[6],
                        "postleitzahl": r[7],
                        "stadt": r[8],
                        "latitude": r[9],
                        "longitude": r[10],
                    },
                    dedupe_key=f"wizard:depots:create:{did}",
                )
        for kid in new_kontakt_ids:
            r = self.cur.execute(
                "SELECT depot_id, name, rolle, telefon, email FROM kontakte WHERE id = ?",
                (kid,),
            ).fetchone()
            if r:
                self.enqueue_sync_change(
                    "kontakte",
                    "create",
                    {
                        "id": int(kid),
                        "depot_id": int(r[0]),
                        "name": r[1],
                        "rolle": r[2],
                        "telefon": r[3],
                        "email": r[4],
                    },
                    dedupe_key=f"wizard:kontakte:create:{kid}",
                )
        for depot_id, praeparat_id, sollbestand in new_dp_keys:
            self.enqueue_sync_change(
                "depot_praeparate",
                "create",
                {
                    "depot_id": int(depot_id),
                    "praeparat_id": int(praeparat_id),
                    "sollbestand": int(sollbestand),
                },
                dedupe_key=f"wizard:depot_praeparate:{depot_id}:{praeparat_id}",
            )

