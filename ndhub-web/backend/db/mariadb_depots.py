"""MariaDB repository mixins (Issue #110)."""

from __future__ import annotations

import logging
from typing import Any

from backend import sql_dialect as sql

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariadbDepotsMixin:
    def list_depots(
        self,
        q: str = "",
        limit: int = 100,
        offset: int = 0,
        allowed_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        safe_ids = sorted({int(item) for item in (allowed_ids or []) if int(item) > 0})
        ids_filter_sql = ""
        ids_params: tuple[Any, ...] = ()
        if safe_ids:
            placeholders = ",".join("%s" for _ in safe_ids)
            ids_filter_sql = "".join([" AND depots.id IN (", placeholders, ")"])
            ids_params = tuple(safe_ids)
        with self._connect() as conn:
            with conn.cursor() as cur:
                sql_parts = [
                    """
                    SELECT depots.id, depots.name, depots.adresse, depots.strasse, depots.hausnummer, depots.postleitzahl, depots.stadt, depots.telefon, depots.email,
                           depots.institution_id, depots.latitude, depots.longitude, institutions.name AS institution_name
                    FROM depots
                    LEFT JOIN institutions ON institutions.id = depots.institution_id
                    WHERE (
                          %s = '%%' OR
                          depots.name LIKE %s OR
                          COALESCE(depots.adresse, '') LIKE %s OR
                          COALESCE(depots.telefon, '') LIKE %s OR
                          COALESCE(depots.email, '') LIKE %s
                    )
                    """,
                ]
                if ids_filter_sql:
                    sql_parts.append(ids_filter_sql)
                sql_parts.append("ORDER BY depots.name LIMIT %s OFFSET %s")
                cur.execute(
                    "".join(sql_parts),
                    (like, like, like, like, like, *ids_params, safe_limit, safe_offset),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def create_depot(
        self,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
        institution_id: int | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Depot-Name darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO depots (name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        safe_name,
                        self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                        (strasse or "").strip() or None,
                        (hausnummer or "").strip() or None,
                        (postleitzahl or "").strip() or None,
                        (stadt or "").strip() or None,
                        (telefon or "").strip() or None,
                        (email or "").strip() or None,
                        int(institution_id) if institution_id is not None else None,
                        float(latitude) if latitude is not None else None,
                        float(longitude) if longitude is not None else None,
                    ),
                )
                conn.commit()
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "create_depot",
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            telefon=telefon,
            email=email,
            institution_id=institution_id,
            latitude=latitude,
            longitude=longitude,
        )
        return new_id

    def update_depot(
        self,
        depot_id: int,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
        institution_id: int | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Depot-Name darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE depots
                    SET name = %s, adresse = %s, strasse = %s, hausnummer = %s, postleitzahl = %s, stadt = %s, telefon = %s, email = %s, institution_id = %s, latitude = %s, longitude = %s
                    WHERE id = %s
                    """,
                    (
                        safe_name,
                        self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                        (strasse or "").strip() or None,
                        (hausnummer or "").strip() or None,
                        (postleitzahl or "").strip() or None,
                        (stadt or "").strip() or None,
                        (telefon or "").strip() or None,
                        (email or "").strip() or None,
                        int(institution_id) if institution_id is not None else None,
                        float(latitude) if latitude is not None else None,
                        float(longitude) if longitude is not None else None,
                        int(depot_id),
                    ),
                )
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write(
            "update_depot",
            depot_id=depot_id,
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            telefon=telefon,
            email=email,
            institution_id=institution_id,
            latitude=latitude,
            longitude=longitude,
        )
        return changed

    def delete_depot(self, depot_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS used_count FROM bewegungen WHERE depot_id = %s", (int(depot_id),))
                used = int(cur.fetchone()["used_count"])
                if used > 0:
                    raise ValueError("Depot kann nicht gelöscht werden, da Bewegungen vorhanden sind.")
                cur.execute("DELETE FROM depots WHERE id = %s", (int(depot_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_depot", depot_id)
        return changed

    def get_depot_name(self, depot_id: int) -> str | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._dialect.format(sql.SQL_GET_DEPOT_NAME),
                    (int(depot_id),),
                )
                row = cur.fetchone()
        return str(row["name"]) if row and row.get("name") is not None else None

    def get_depot(self, depot_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._dialect.format(sql.SQL_GET_DEPOT),
                    (int(depot_id),),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def list_praeparate_for_depot(self, depot_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT praeparat_id FROM depot_praeparate WHERE depot_id = %s",
                    (int(depot_id),),
                )
                assigned_rows = cur.fetchall()
                assigned_ids = {int(row["praeparat_id"]) for row in assigned_rows}
                if not assigned_ids:
                    cur.execute("SELECT id, name FROM praeparate ORDER BY name")
                    return [dict(row) for row in cur.fetchall()]
                placeholders = ", ".join(["%s"] * len(assigned_ids))
                sql = "".join(
                    [
                        "SELECT id, name FROM praeparate WHERE id IN (",
                        placeholders,
                        ") ORDER BY name",
                    ]
                )
                cur.execute(sql, tuple(sorted(assigned_ids)))
                return [dict(row) for row in cur.fetchall()]

    def list_depot_assignments(self, depot_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        p.id AS praeparat_id,
                        p.name AS praeparat_name,
                        CASE WHEN dp.praeparat_id IS NULL THEN 0 ELSE 1 END AS assigned,
                        COALESCE(dp.sollbestand, 0) AS sollbestand
                    FROM praeparate p
                    LEFT JOIN depot_praeparate dp
                        ON dp.praeparat_id = p.id AND dp.depot_id = %s
                    ORDER BY p.name
                    """,
                    (int(depot_id),),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def set_depot_assignments(self, depot_id: int, assignments: list[dict[str, Any]]) -> None:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM depots WHERE id = %s", (safe_depot_id,))
                if cur.fetchone() is None:
                    raise ValueError("Depot nicht gefunden.")
                cur.execute("DELETE FROM depot_praeparate WHERE depot_id = %s", (safe_depot_id,))
                for entry in assignments:
                    praeparat_id = int(entry["praeparat_id"])
                    sollbestand = int(entry.get("sollbestand", 0))
                    if sollbestand < 0:
                        raise ValueError("Sollbestand darf nicht negativ sein.")
                    cur.execute("SELECT id FROM praeparate WHERE id = %s", (praeparat_id,))
                    if cur.fetchone() is None:
                        raise ValueError(f"Praeparat existiert nicht: {praeparat_id}")
                    cur.execute(
                        """
                        INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                        VALUES (%s, %s, %s)
                        """,
                        (safe_depot_id, praeparat_id, sollbestand),
                    )
                conn.commit()
        self._mirror_write("set_depot_assignments", depot_id=safe_depot_id, assignments=assignments)
