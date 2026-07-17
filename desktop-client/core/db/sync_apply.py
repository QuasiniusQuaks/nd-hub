"""Remote-Sync Apply (Issue #66 Phase 2).

LOC-Split: ``apply_remote_sync_change`` aus ``db_manager.Database``.
"""
from __future__ import annotations

from typing import Any


def _sync_payload_str(data: dict[str, Any], key: str) -> Any:
    v = data.get(key)
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _sync_payload_float(data: dict[str, Any], key: str) -> Any:
    v = data.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class SyncApplyMixin:
    """Wendet vom Server gepullte Änderungen lokal an. Issue #66.

    Erwartet: ``self.cur``, ``self.conn``, ``_clear_lookup_caches``,
    ``get_depot_id_by_name``, ``get_praeparat_id_by_name``.
    """

    def apply_remote_sync_change(self, entity_name: str, operation: str, payload: dict[str, Any]) -> bool:
        """Wendet vom Server gepullte Aenderungen lokal an (ohne Outbox-Queueing)."""
        entity = (entity_name or "").strip().lower()
        op = (operation or "").strip().lower()
        data = dict(payload or {})

        if entity == "depots":
            depot_id = int(data.get("id") or 0)
            if op == "delete":
                if depot_id > 0:
                    self.cur.execute("DELETE FROM depots WHERE id = ?", (depot_id,))
                    self.conn.commit()
                    self._clear_lookup_caches()
                return True
            if depot_id <= 0:
                return False
            existing = self.cur.execute("SELECT id FROM depots WHERE id = ?", (depot_id,)).fetchone()
            values = (
                str(data.get("name") or ""),
                data.get("adresse"),
                _sync_payload_str(data, "strasse"),
                _sync_payload_str(data, "hausnummer"),
                _sync_payload_str(data, "postleitzahl"),
                _sync_payload_str(data, "stadt"),
                data.get("telefon"),
                data.get("email"),
                int(data.get("institution_id")) if data.get("institution_id") is not None else None,
                _sync_payload_float(data, "latitude"),
                _sync_payload_float(data, "longitude"),
                depot_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE depots SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?,
                        telefon = ?, email = ?, institution_id = ?, latitude = ?, longitude = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO depots (
                        name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id,
                        latitude, longitude, id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            self._clear_lookup_caches()
            return True

        if entity == "institutions":
            institution_id = int(data.get("id") or 0)
            if op == "delete":
                if institution_id > 0:
                    self.cur.execute("DELETE FROM institutions WHERE id = ?", (institution_id,))
                    self.conn.commit()
                    self._clear_lookup_caches()
                return True
            if institution_id <= 0:
                return False
            existing = self.cur.execute("SELECT id FROM institutions WHERE id = ?", (institution_id,)).fetchone()
            values = (
                str(data.get("name") or ""),
                data.get("adresse"),
                _sync_payload_str(data, "strasse"),
                _sync_payload_str(data, "hausnummer"),
                _sync_payload_str(data, "postleitzahl"),
                _sync_payload_str(data, "stadt"),
                _sync_payload_float(data, "latitude"),
                _sync_payload_float(data, "longitude"),
                institution_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE institutions SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?,
                        latitude = ?, longitude = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO institutions (
                        name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude, id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            self._clear_lookup_caches()
            return True

        if entity == "praeparate":
            prae_id = int(data.get("id") or 0)
            if op == "delete":
                if prae_id > 0:
                    self.cur.execute("DELETE FROM praeparate WHERE id = ?", (prae_id,))
                    self.conn.commit()
                    self._clear_lookup_caches()
                return True
            if prae_id <= 0:
                return False
            existing = self.cur.execute("SELECT id FROM praeparate WHERE id = ?", (prae_id,)).fetchone()
            values = (
                str(data.get("name") or ""),
                data.get("wirkstoff"),
                data.get("darreichungsform"),
                data.get("staerke"),
                data.get("einheit"),
                data.get("pzn"),
                data.get("hersteller"),
                prae_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE praeparate
                    SET name = ?, wirkstoff = ?, darreichungsform = ?, staerke = ?, einheit = ?, pzn = ?, hersteller = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            self._clear_lookup_caches()
            return True

        if entity == "kontakte":
            kontakt_id = int(data.get("id") or 0)
            if op == "delete":
                if kontakt_id > 0:
                    self.cur.execute("DELETE FROM kontakte WHERE id = ?", (kontakt_id,))
                    self.conn.commit()
                return True
            if kontakt_id <= 0:
                return False
            depot_id = int(data.get("depot_id") or 0)
            existing = self.cur.execute("SELECT id FROM kontakte WHERE id = ?", (kontakt_id,)).fetchone()
            values = (
                depot_id,
                str(data.get("name") or ""),
                data.get("rolle"),
                data.get("telefon"),
                data.get("email"),
                kontakt_id,
            )
            if existing:
                self.cur.execute(
                    "UPDATE kontakte SET depot_id = ?, name = ?, rolle = ?, telefon = ?, email = ? WHERE id = ?",
                    values,
                )
            else:
                self.cur.execute(
                    "INSERT INTO kontakte (depot_id, name, rolle, telefon, email, id) VALUES (?, ?, ?, ?, ?, ?)",
                    values,
                )
            self.conn.commit()
            return True

        if entity == "bewegungen":
            bewegung_id = int(data.get("id") or 0)
            if op == "delete":
                if bewegung_id > 0:
                    self.cur.execute("DELETE FROM bewegungen WHERE id = ?", (bewegung_id,))
                    self.conn.commit()
                return True
            if bewegung_id <= 0:
                return False
            typ_raw = str(data.get("typ") or "").strip()
            typ = {
                "zugang": "Zugang",
                "abgang": "Abgang",
                "vernichtung": "Vernichtung",
            }.get(typ_raw.lower(), typ_raw)
            datum = data.get("datum")
            eingang = datum if typ == "Zugang" else None
            ausgang = datum if typ in {"Abgang", "Vernichtung"} else None

            depot_id = int(data.get("depot_id") or 0)
            praeparat_id = int(data.get("praeparat_id") or 0)
            depot_name = str(data.get("depot_name") or "").strip()
            praeparat_name = str(data.get("praeparat_name") or "").strip()

            if depot_name:
                mapped_depot = self.get_depot_id_by_name(depot_name)
                if mapped_depot:
                    depot_id = int(mapped_depot)
            elif depot_id > 0:
                depot_exists = self.cur.execute("SELECT id FROM depots WHERE id = ?", (depot_id,)).fetchone()
                if depot_exists is None:
                    depot_id = 0

            if praeparat_name:
                mapped_praeparat = self.get_praeparat_id_by_name(praeparat_name)
                if mapped_praeparat:
                    praeparat_id = int(mapped_praeparat)
            elif praeparat_id > 0:
                prae_exists = self.cur.execute("SELECT id FROM praeparate WHERE id = ?", (praeparat_id,)).fetchone()
                if prae_exists is None:
                    praeparat_id = 0

            if depot_id <= 0 or praeparat_id <= 0 or typ not in {"Zugang", "Abgang", "Vernichtung"}:
                return False

            existing = self.cur.execute("SELECT id FROM bewegungen WHERE id = ?", (bewegung_id,)).fetchone()
            values = (
                depot_id,
                praeparat_id,
                str(data.get("charge") or ""),
                str(data.get("verfall") or ""),
                eingang,
                ausgang,
                data.get("empfaenger"),
                int(data.get("anzahl") or 0),
                typ,
                bewegung_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE bewegungen
                    SET depot_id = ?, praeparat_id = ?, charge = ?, verfall = ?, eingang_datum = ?, ausgang_datum = ?,
                        empfaenger = ?, anzahl = ?, typ = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO bewegungen (
                        depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum,
                        empfaenger, anzahl, typ, id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            return True

        if entity == "depot_praeparate":
            depot_id = int(data.get("depot_id") or 0)
            praeparat_id = int(data.get("praeparat_id") or 0)
            if op == "delete":
                if depot_id > 0 and praeparat_id > 0:
                    self.cur.execute(
                        "DELETE FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                        (depot_id, praeparat_id),
                    )
                else:
                    assignment_id = int(data.get("id") or 0)
                    if assignment_id <= 0:
                        return False
                    self.cur.execute("DELETE FROM depot_praeparate WHERE id = ?", (assignment_id,))
                self.conn.commit()
                return True
            if depot_id <= 0 or praeparat_id <= 0:
                return False
            sollbestand = max(0, int(data.get("sollbestand") or 0))
            existing = self.cur.execute(
                "SELECT id FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                (depot_id, praeparat_id),
            ).fetchone()
            if existing:
                self.cur.execute(
                    "UPDATE depot_praeparate SET sollbestand = ? WHERE depot_id = ? AND praeparat_id = ?",
                    (sollbestand, depot_id, praeparat_id),
                )
            else:
                self.cur.execute(
                    "INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (?, ?, ?)",
                    (depot_id, praeparat_id, sollbestand),
                )
            self.conn.commit()
            return True

        return False

