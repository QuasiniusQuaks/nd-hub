"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

from typing import Any

from backend import sql_dialect as sql

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqlitePraeparateMixin:
    def list_praeparate(self, q: str = "", limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                self._dialect.format(sql.SQL_LIST_PRAEPARATE),
                (like, like, safe_limit, safe_offset),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_praeparat(
        self,
        name: str,
        wirkstoff: str | None = None,
        darreichungsform: str | None = None,
        staerke: str | None = None,
        einheit: str | None = None,
        pzn: str | None = None,
        hersteller: str | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Praeparat-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_name,
                    (wirkstoff or "").strip() or None,
                    (darreichungsform or "").strip() or None,
                    (staerke or "").strip() or None,
                    (einheit or "").strip() or None,
                    (pzn or "").strip() or None,
                    (hersteller or "").strip() or None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_praeparat(
        self,
        praeparat_id: int,
        name: str,
        wirkstoff: str | None = None,
        darreichungsform: str | None = None,
        staerke: str | None = None,
        einheit: str | None = None,
        pzn: str | None = None,
        hersteller: str | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Praeparat-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE praeparate
                SET name = ?, wirkstoff = ?, darreichungsform = ?, staerke = ?, einheit = ?, pzn = ?, hersteller = ?
                WHERE id = ?
                """,
                (
                    safe_name,
                    (wirkstoff or "").strip() or None,
                    (darreichungsform or "").strip() or None,
                    (staerke or "").strip() or None,
                    (einheit or "").strip() or None,
                    (pzn or "").strip() or None,
                    (hersteller or "").strip() or None,
                    int(praeparat_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_praeparat(self, praeparat_id: int) -> bool:
        safe_id = int(praeparat_id)
        with self._connect() as conn:
            cur = conn.cursor()
            used = cur.execute(
                "SELECT COUNT(*) FROM bewegungen WHERE praeparat_id = ?",
                (safe_id,),
            ).fetchone()[0]
            if used > 0:
                raise ValueError("Praeparat kann nicht geloescht werden, da Bewegungen vorhanden sind.")
            cur.execute("DELETE FROM praeparate WHERE id = ?", (safe_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_praeparat(self, praeparat_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                self._dialect.format(sql.SQL_GET_PRAEPARAT),
                (int(praeparat_id),),
            ).fetchone()
            return dict(row) if row else None
