"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteKontakteMixin:
    def list_kontakte(self, depot_id: int) -> list[dict[str, Any]]:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, depot_id, name, rolle, telefon, email
                FROM kontakte
                WHERE depot_id = ?
                ORDER BY name, id
                """,
                (safe_depot_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_kontakt(
        self,
        depot_id: int,
        name: str,
        rolle: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontakt-Name darf nicht leer sein.")
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (safe_depot_id,),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot nicht gefunden.")
            cur.execute(
                """
                INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    safe_depot_id,
                    safe_name,
                    (rolle or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_kontakt(
        self,
        kontakt_id: int,
        name: str,
        rolle: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontakt-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE kontakte
                SET name = ?, rolle = ?, telefon = ?, email = ?
                WHERE id = ?
                """,
                (
                    safe_name,
                    (rolle or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
                    int(kontakt_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_kontakt(self, kontakt_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM kontakte WHERE id = ?", (int(kontakt_id),))
            conn.commit()
            return cur.rowcount > 0

    def get_kontakt(self, kontakt_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, depot_id, name, rolle, telefon, email FROM kontakte WHERE id = ?",
                (int(kontakt_id),),
            ).fetchone()
            return dict(row) if row else None

    def get_kontakte_by_depot_ids(self, depot_ids: list[int]) -> list[dict[str, Any]]:
        safe_ids = sorted({int(depot_id) for depot_id in depot_ids})
        if not safe_ids:
            return []
        placeholders = ",".join("?" for _ in safe_ids)
        sql = "".join(
            [
                """
                SELECT
                    k.id,
                    k.name,
                    k.rolle,
                    k.email,
                    d.name AS depot_name,
                    d.id AS depot_id
                FROM kontakte k
                JOIN depots d ON d.id = k.depot_id
                WHERE k.depot_id IN (""",
                placeholders,
                """)
                  AND COALESCE(k.email, '') <> ''
                ORDER BY d.name, k.name
                """,
            ]
        )
        with self._connect() as conn:
            rows = conn.execute(
                sql,
                tuple(safe_ids),
            ).fetchall()
            return [dict(row) for row in rows]
