"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

import sqlite3
from typing import Any

from backend import sql_dialect as sql

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteDepotsMixin:
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
            placeholders = ",".join("?" for _ in safe_ids)
            ids_filter_sql = "".join([" AND depots.id IN (", placeholders, ")"])
            ids_params = tuple(safe_ids)
        with self._connect() as conn:
            sql_parts = [
                """
                SELECT depots.id, depots.name, depots.adresse, depots.strasse, depots.hausnummer, depots.postleitzahl, depots.stadt, depots.telefon, depots.email,
                       depots.institution_id, depots.latitude, depots.longitude, institutions.name AS institution_name
                FROM depots
                LEFT JOIN institutions ON institutions.id = depots.institution_id
                WHERE (
                      ? = '%%' OR
                      depots.name LIKE ? OR
                      COALESCE(depots.adresse, '') LIKE ? OR
                      COALESCE(depots.telefon, '') LIKE ? OR
                      COALESCE(depots.email, '') LIKE ?
                )
                """,
            ]
            if ids_filter_sql:
                sql_parts.append(ids_filter_sql)
            sql_parts.append("ORDER BY depots.name LIMIT ? OFFSET ?")
            rows = conn.execute(
                "".join(sql_parts),
                (like, like, like, like, like, *ids_params, safe_limit, safe_offset),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_praeparate_for_depot(self, depot_id: int) -> list[dict[str, Any]]:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            assigned_rows = conn.execute(
                "SELECT praeparat_id FROM depot_praeparate WHERE depot_id = ?",
                (safe_depot_id,),
            ).fetchall()
            assigned_ids = {row["praeparat_id"] for row in assigned_rows}
            if not assigned_ids:
                rows = conn.execute(
                    "SELECT id, name FROM praeparate ORDER BY name",
                ).fetchall()
                return [dict(row) for row in rows]
            placeholders = ",".join("?" * len(assigned_ids))
            sql = "".join(
                [
                    "SELECT id, name FROM praeparate WHERE id IN (",
                    placeholders,
                    ") ORDER BY name",
                ]
            )
            rows = conn.execute(
                sql,
                tuple(sorted(assigned_ids)),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_depot_assignments(self, depot_id: int) -> list[dict[str, Any]]:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.id AS praeparat_id,
                    p.name AS praeparat_name,
                    CASE WHEN dp.praeparat_id IS NULL THEN 0 ELSE 1 END AS assigned,
                    COALESCE(dp.sollbestand, 0) AS sollbestand
                FROM praeparate p
                LEFT JOIN depot_praeparate dp
                    ON dp.praeparat_id = p.id AND dp.depot_id = ?
                ORDER BY p.name
                """,
                (safe_depot_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def set_depot_assignments(self, depot_id: int, assignments: list[dict[str, Any]]) -> None:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (safe_depot_id,),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot nicht gefunden.")
            cur.execute("DELETE FROM depot_praeparate WHERE depot_id = ?", (safe_depot_id,))
            for entry in assignments:
                praeparat_id = int(entry["praeparat_id"])
                sollbestand = int(entry.get("sollbestand", 0))
                if sollbestand < 0:
                    raise ValueError("Sollbestand darf nicht negativ sein.")
                prae_exists = cur.execute(
                    "SELECT id FROM praeparate WHERE id = ?",
                    (praeparat_id,),
                ).fetchone()
                if prae_exists is None:
                    raise ValueError(f"Praeparat existiert nicht: {praeparat_id}")
                cur.execute(
                    """
                    INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                    VALUES (?, ?, ?)
                    """,
                    (safe_depot_id, praeparat_id, sollbestand),
                )
            conn.commit()

    def get_depot_assignment(self, depot_id: int, praeparat_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, depot_id, praeparat_id, sollbestand
                FROM depot_praeparate
                WHERE depot_id = ? AND praeparat_id = ?
                """,
                (int(depot_id), int(praeparat_id)),
            ).fetchone()
            return dict(row) if row else None

    def get_depot_assignment_by_id(self, assignment_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, depot_id, praeparat_id, sollbestand
                FROM depot_praeparate
                WHERE id = ?
                """,
                (int(assignment_id),),
            ).fetchone()
            return dict(row) if row else None

    def upsert_depot_assignment(self, depot_id: int, praeparat_id: int, sollbestand: int = 0) -> int:
        safe_depot_id = int(depot_id)
        safe_praeparat_id = int(praeparat_id)
        safe_soll = max(0, int(sollbestand))
        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (safe_depot_id,),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot nicht gefunden.")
            prae_exists = cur.execute(
                "SELECT id FROM praeparate WHERE id = ?",
                (safe_praeparat_id,),
            ).fetchone()
            if prae_exists is None:
                raise ValueError("Praeparat nicht gefunden.")
            existing = cur.execute(
                "SELECT id FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                (safe_depot_id, safe_praeparat_id),
            ).fetchone()
            if existing is None:
                cur.execute(
                    """
                    INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                    VALUES (?, ?, ?)
                    """,
                    (safe_depot_id, safe_praeparat_id, safe_soll),
                )
                conn.commit()
                return int(cur.lastrowid)
            assignment_id = int(existing["id"] if isinstance(existing, sqlite3.Row) else existing[0])
            cur.execute(
                "UPDATE depot_praeparate SET sollbestand = ? WHERE id = ?",
                (safe_soll, assignment_id),
            )
            conn.commit()
            return assignment_id

    def delete_depot_assignment(self, depot_id: int, praeparat_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                (int(depot_id), int(praeparat_id)),
            )
            conn.commit()
            return cur.rowcount > 0

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
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO depots (name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            return int(cur.lastrowid)

    def get_depot_name(self, depot_id: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                self._dialect.format(sql.SQL_GET_DEPOT_NAME),
                (int(depot_id),),
            ).fetchone()
            if row is None:
                return None
            return str(row["name"]) if row["name"] is not None else None

    def get_depot(self, depot_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                self._dialect.format(sql.SQL_GET_DEPOT),
                (int(depot_id),),
            ).fetchone()
            return dict(row) if row else None

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
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE depots
                SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?, telefon = ?, email = ?, institution_id = ?, latitude = ?, longitude = ?
                WHERE id = ?
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
            conn.commit()
            return cur.rowcount > 0

    def delete_depot(self, depot_id: int) -> bool:
        safe_id = int(depot_id)
        with self._connect() as conn:
            cur = conn.cursor()
            used = cur.execute(
                "SELECT COUNT(*) FROM bewegungen WHERE depot_id = ?",
                (safe_id,),
            ).fetchone()[0]
            if used > 0:
                raise ValueError("Depot kann nicht geloescht werden, da Bewegungen vorhanden sind.")
            cur.execute("DELETE FROM depots WHERE id = ?", (safe_id,))
            conn.commit()
            return cur.rowcount > 0
