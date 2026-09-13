"""MariaDB repository mixins (Issue #110)."""

from __future__ import annotations

import logging
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariadbKontakteMixin:
    def list_kontakte(self, depot_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, depot_id, name, rolle, telefon, email
                    FROM kontakte
                    WHERE depot_id = %s
                    ORDER BY name
                    """,
                    (int(depot_id),),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def create_kontakt(self, depot_id: int, name: str, rolle: str | None = None, telefon: str | None = None, email: str | None = None) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontaktname darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        int(depot_id),
                        safe_name,
                        (rolle or "").strip() or None,
                        (telefon or "").strip() or None,
                        (email or "").strip() or None,
                    ),
                )
                conn.commit()
                new_id = int(cur.lastrowid)
        self._mirror_write("create_kontakt", depot_id=depot_id, name=safe_name, rolle=rolle, telefon=telefon, email=email)
        return new_id

    def update_kontakt(self, kontakt_id: int, name: str, rolle: str | None = None, telefon: str | None = None, email: str | None = None) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontaktname darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE kontakte
                    SET name = %s, rolle = %s, telefon = %s, email = %s
                    WHERE id = %s
                    """,
                    (
                        safe_name,
                        (rolle or "").strip() or None,
                        (telefon or "").strip() or None,
                        (email or "").strip() or None,
                        int(kontakt_id),
                    ),
                )
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("update_kontakt", kontakt_id=kontakt_id, name=safe_name, rolle=rolle, telefon=telefon, email=email)
        return changed

    def delete_kontakt(self, kontakt_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM kontakte WHERE id = %s", (int(kontakt_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_kontakt", kontakt_id)
        return changed

    def get_kontakt(self, kontakt_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, depot_id, name, rolle, telefon, email FROM kontakte WHERE id = %s",
                    (int(kontakt_id),),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def get_kontakte_by_depot_ids(self, depot_ids: list[int]) -> list[dict[str, Any]]:
        if not depot_ids:
            return []
        placeholders = ", ".join(["%s"] * len(depot_ids))
        sql = "".join(
            [
                """
                SELECT k.id, k.depot_id, k.name, k.rolle, k.telefon, k.email, d.name AS depot_name
                FROM kontakte k
                JOIN depots d ON d.id = k.depot_id
                WHERE k.depot_id IN (""",
                placeholders,
                """) AND COALESCE(k.email, '') <> ''
                ORDER BY d.name, k.name
                """,
            ]
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(int(item) for item in depot_ids))
                rows = cur.fetchall()
        return [dict(row) for row in rows]
