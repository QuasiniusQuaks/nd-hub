"""Stammdaten-CRUD (Depots, Präparate, Kontakte, Permissions). Issue #66 Phase 4."""
from __future__ import annotations

from typing import Any

from core.cache_helpers import cached_method
from core.db.helpers import _MISSING, _coerce_opt_float


class StammdatenMixin:
    """Stammdaten/Lookups. Erwartet cur/conn, _clear_lookup_caches, Sync-Outbox-Hooks."""

    @cached_method(ttl_seconds=300, maxsize=64)
    def list_depots(self):
        return self.cur.execute(
            """
            SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id,
                   latitude, longitude
            FROM depots ORDER BY name
            """
        ).fetchall()

    def list_depots_for_scope(self, security_manager=None):
        """
        Depots fuer die aktuelle Sicht. Single-Tenant-Desktop: identisch zu list_depots.
        Hook fuer spaeteres Filtern nach Institution, wenn cross_institution_read fehlt.
        """
        if security_manager is not None and hasattr(
            security_manager, "can_view_cross_institution_masterdata"
        ):
            _ = security_manager.can_view_cross_institution_masterdata()
        return self.list_depots()

    def add_depot(
        self,
        name,
        adresse,
        telefon,
        email,
        institution_id=None,
        strasse=None,
        hausnummer=None,
        postleitzahl=None,
        stadt=None,
        latitude=None,
        longitude=None,
    ):
        s_str = str(strasse).strip() or None if strasse is not None else None
        s_hnr = str(hausnummer).strip() or None if hausnummer is not None else None
        s_plz = str(postleitzahl).strip() or None if postleitzahl is not None else None
        s_stadt = str(stadt).strip() or None if stadt is not None else None
        lat = _coerce_opt_float(latitude)
        lon = _coerce_opt_float(longitude)
        self.cur.execute(
            """
            INSERT INTO depots (
                name, adresse, telefon, email, institution_id, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                name,
                adresse,
                telefon,
                email,
                institution_id,
                s_str,
                s_hnr,
                s_plz,
                s_stadt,
                lat,
                lon,
            ),
        )
        self.conn.commit()
        depot_id = self.cur.lastrowid
        self.enqueue_sync_change(
            entity_name="depots",
            operation="create",
            payload={
                "id": int(depot_id),
                "name": name,
                "adresse": adresse,
                "strasse": s_str,
                "hausnummer": s_hnr,
                "postleitzahl": s_plz,
                "stadt": s_stadt,
                "telefon": telefon,
                "email": email,
                "institution_id": institution_id,
                "latitude": lat,
                "longitude": lon,
            },
        )
        self._clear_lookup_caches()
        return depot_id

    def update_depot(
        self,
        depot_id,
        name,
        adresse,
        telefon,
        email,
        institution_id=None,
        strasse=_MISSING,
        hausnummer=_MISSING,
        postleitzahl=_MISSING,
        stadt=_MISSING,
        latitude=_MISSING,
        longitude=_MISSING,
    ):
        prev = self.cur.execute(
            "SELECT strasse, hausnummer, postleitzahl, stadt, latitude, longitude FROM depots WHERE id = ?",
            (depot_id,),
        ).fetchone()
        if not prev:
            return

        def _txt(new_val: Any, old: Any) -> Any:
            if new_val is _MISSING:
                return old
            if new_val is None:
                return None
            s = str(new_val).strip()
            return s or None

        def _flt(new_val: Any, old: Any) -> Any:
            if new_val is _MISSING:
                return old
            return _coerce_opt_float(new_val)

        s_str = _txt(strasse, prev[0])
        s_hnr = _txt(hausnummer, prev[1])
        s_plz = _txt(postleitzahl, prev[2])
        s_stadt = _txt(stadt, prev[3])
        lat = _flt(latitude, prev[4])
        lon = _flt(longitude, prev[5])
        self.cur.execute(
            """
            UPDATE depots SET name=?, adresse=?, telefon=?, email=?, institution_id=?,
                strasse=?, hausnummer=?, postleitzahl=?, stadt=?, latitude=?, longitude=?
            WHERE id=?
            """,
            (
                name,
                adresse,
                telefon,
                email,
                institution_id,
                s_str,
                s_hnr,
                s_plz,
                s_stadt,
                lat,
                lon,
                depot_id,
            ),
        )
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="depots",
            operation="update",
            payload={
                "id": int(depot_id),
                "name": name,
                "adresse": adresse,
                "strasse": s_str,
                "hausnummer": s_hnr,
                "postleitzahl": s_plz,
                "stadt": s_stadt,
                "telefon": telefon,
                "email": email,
                "institution_id": institution_id,
                "latitude": lat,
                "longitude": lon,
            },
        )
        self._clear_lookup_caches()

    def list_institutions(self):
        return self.cur.execute(
            """
            SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
            FROM institutions ORDER BY name
            """
        ).fetchall()

    def upsert_user_depot_permission(self, username: str, depot_id: int, can_read: bool, can_write: bool):
        self.cur.execute(
            """
            INSERT INTO user_depot_permissions (username, depot_id, can_read, can_write)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username, depot_id) DO UPDATE SET
                can_read = excluded.can_read,
                can_write = excluded.can_write
            """,
            (username, int(depot_id), int(bool(can_read)), int(bool(can_write))),
        )
        self.conn.commit()

    def list_user_depot_permissions(self, username: str):
        return self.cur.execute(
            """
            SELECT depot_id, can_read, can_write
            FROM user_depot_permissions
            WHERE username = ?
            ORDER BY depot_id
            """,
            (username,),
        ).fetchall()

    def delete_depot(self, depot_id):
        self.cur.execute("DELETE FROM depots WHERE id=?", (depot_id,))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="depots",
            operation="delete",
            payload={"id": int(depot_id)},
        )
        self._clear_lookup_caches()



    # ----- Präparate -----
    @cached_method(ttl_seconds=300, maxsize=64)
    def list_praeparate(self):
        return self.cur.execute("SELECT id, name FROM praeparate ORDER BY name").fetchall()

    @cached_method(ttl_seconds=300, maxsize=64)
    def list_praeparate_extended(self):
        return self.cur.execute(
            """
            SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
            FROM praeparate
            ORDER BY name
            """
        ).fetchall()

    def add_praeparat(self, name):
        return self.add_praeparat_extended(
            name=name,
            wirkstoff="",
            darreichungsform="",
            staerke="",
            einheit="",
            pzn="",
            hersteller="",
        )

    def add_praeparat_extended(
        self,
        name: str,
        wirkstoff: str = "",
        darreichungsform: str = "",
        staerke: str = "",
        einheit: str = "",
        pzn: str = "",
        hersteller: str = "",
    ):
        self.cur.execute(
            """
            INSERT INTO praeparate
                (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                (wirkstoff or "").strip() or None,
                (darreichungsform or "").strip() or None,
                (staerke or "").strip() or None,
                (einheit or "").strip() or None,
                (pzn or "").strip() or None,
                (hersteller or "").strip() or None,
            ),
        )
        self.conn.commit()
        prae_id = self.cur.lastrowid
        self.enqueue_sync_change(
            entity_name="praeparate",
            operation="create",
            payload={
                "id": int(prae_id),
                "name": name,
                "wirkstoff": (wirkstoff or "").strip() or None,
                "darreichungsform": (darreichungsform or "").strip() or None,
                "staerke": (staerke or "").strip() or None,
                "einheit": (einheit or "").strip() or None,
                "pzn": (pzn or "").strip() or None,
                "hersteller": (hersteller or "").strip() or None,
            },
        )
        self._clear_lookup_caches()
        return prae_id

    def update_praeparat(self, prae_id, name):
        self.update_praeparat_extended(
            prae_id=prae_id,
            name=name,
            wirkstoff="",
            darreichungsform="",
            staerke="",
            einheit="",
            pzn="",
            hersteller="",
        )

    def update_praeparat_extended(
        self,
        prae_id: int,
        name: str,
        wirkstoff: str = "",
        darreichungsform: str = "",
        staerke: str = "",
        einheit: str = "",
        pzn: str = "",
        hersteller: str = "",
    ):
        self.cur.execute(
            """
            UPDATE praeparate
            SET name=?, wirkstoff=?, darreichungsform=?, staerke=?, einheit=?, pzn=?, hersteller=?
            WHERE id=?
            """,
            (
                name,
                (wirkstoff or "").strip() or None,
                (darreichungsform or "").strip() or None,
                (staerke or "").strip() or None,
                (einheit or "").strip() or None,
                (pzn or "").strip() or None,
                (hersteller or "").strip() or None,
                prae_id,
            ),
        )
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="praeparate",
            operation="update",
            payload={
                "id": int(prae_id),
                "name": name,
                "wirkstoff": (wirkstoff or "").strip() or None,
                "darreichungsform": (darreichungsform or "").strip() or None,
                "staerke": (staerke or "").strip() or None,
                "einheit": (einheit or "").strip() or None,
                "pzn": (pzn or "").strip() or None,
                "hersteller": (hersteller or "").strip() or None,
            },
        )
        self._clear_lookup_caches()

    def delete_praeparat(self, prae_id):
        self.cur.execute("DELETE FROM praeparate WHERE id=?", (prae_id,))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="praeparate",
            operation="delete",
            payload={"id": int(prae_id)},
        )
        self._clear_lookup_caches()

    # ----- Zuordnung Depot ↔ Präparate mit Sollbestand -----
    def get_assigned_praeparate(self, depot_id):
        rows = self.cur.execute("SELECT praeparat_id FROM depot_praeparate WHERE depot_id=?", (depot_id,)).fetchall()
        return set(r[0] for r in rows)

    def get_depot_praeparat_assignments(self, depot_id):
        rows = self.cur.execute("""
            SELECT praeparat_id, sollbestand
            FROM depot_praeparate
            WHERE depot_id=?
        """, (depot_id,)).fetchall()
        return {r[0]: r[1] if r[1] is not None else 0 for r in rows}

    def set_assigned_praeparate_with_sollbestand(self, depot_id, praeparat_sollbestand_dict):
        before_rows = self.cur.execute(
            "SELECT praeparat_id FROM depot_praeparate WHERE depot_id=?",
            (depot_id,),
        ).fetchall()
        before_ids = {int(r[0]) for r in before_rows}
        self.cur.execute("DELETE FROM depot_praeparate WHERE depot_id=?", (depot_id,))
        for pid, sollbestand in praeparat_sollbestand_dict.items():
            self.cur.execute("""
                INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                VALUES (?, ?, ?)
            """, (depot_id, pid, sollbestand))
        self.conn.commit()
        after_ids = {int(pid) for pid in praeparat_sollbestand_dict.keys()}
        deleted_ids = before_ids - after_ids
        for praeparat_id in deleted_ids:
            self.enqueue_sync_change(
                entity_name="depot_praeparate",
                operation="delete",
                payload={"depot_id": int(depot_id), "praeparat_id": int(praeparat_id)},
            )
        for pid, sollbestand in praeparat_sollbestand_dict.items():
            self.enqueue_sync_change(
                entity_name="depot_praeparate",
                operation="update",
                payload={
                    "depot_id": int(depot_id),
                    "praeparat_id": int(pid),
                    "sollbestand": int(sollbestand or 0),
                },
            )
        self._clear_lookup_caches()

    # ----- Ansprechpartner -----
    def list_kontakte(self, depot_id):
        return self.cur.execute("SELECT id, name, rolle, telefon, email FROM kontakte WHERE depot_id=? ORDER BY name", (depot_id,)).fetchall()

    def add_kontakt(self, depot_id, name, rolle, telefon, email):
        self.cur.execute("INSERT INTO kontakte (depot_id, name, rolle, telefon, email) VALUES (?,?,?,?,?)",
                        (depot_id, name, rolle, telefon, email))
        self.conn.commit()
        kontakt_id = self.cur.lastrowid
        self.enqueue_sync_change(
            entity_name="kontakte",
            operation="create",
            payload={
                "id": int(kontakt_id),
                "depot_id": int(depot_id),
                "name": name,
                "rolle": rolle,
                "telefon": telefon,
                "email": email,
            },
        )
        return kontakt_id

    def update_kontakt(self, kontakt_id, name, rolle, telefon, email):
        self.cur.execute("UPDATE kontakte SET name=?, rolle=?, telefon=?, email=? WHERE id=?",
                        (name, rolle, telefon, email, kontakt_id))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="kontakte",
            operation="update",
            payload={
                "id": int(kontakt_id),
                "name": name,
                "rolle": rolle,
                "telefon": telefon,
                "email": email,
            },
        )

    def delete_kontakt(self, kontakt_id):
        self.cur.execute("DELETE FROM kontakte WHERE id=?", (kontakt_id,))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="kontakte",
            operation="delete",
            payload={"id": int(kontakt_id)},
        )

    # ----- E-Mail-Funktionen -----
    def get_kontakte_by_depot_ids(self, depot_ids):
        if not depot_ids:
            return []

        # Scanner-Schutz (False Positive Prävention): Typisierung erzwingen
        safe_depot_ids = tuple(int(d) for d in depot_ids)
        placeholders = ','.join('?' * len(safe_depot_ids))
        # Placeholders are exclusively '?' generated from the count of
        # already-validated integer IDs; no user input reaches the SQL.
        sql = f"""
            SELECT k.id, k.name, k.rolle, k.email, d.name as depot_name, d.id as depot_id
            FROM kontakte k
            JOIN depots d ON d.id = k.depot_id
            WHERE k.depot_id IN ({placeholders})
              AND k.email IS NOT NULL
              AND k.email != ''
            ORDER BY d.name, k.name
        """  # nosec B608
        return self.cur.execute(sql, safe_depot_ids).fetchall()





