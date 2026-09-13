"""MariaDB repository mixins (Issue #110)."""

from __future__ import annotations

import logging
from typing import Any

from backend import sql_dialect as sql

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariadbPraeparateMixin:
    def list_praeparate(self, q: str = "", limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._dialect.format(sql.SQL_LIST_PRAEPARATE),
                    (like, like, safe_limit, safe_offset),
                )
                rows = cur.fetchall()
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "create_praeparat",
            name=safe_name,
            wirkstoff=wirkstoff,
            darreichungsform=darreichungsform,
            staerke=staerke,
            einheit=einheit,
            pzn=pzn,
            hersteller=hersteller,
        )
        return new_id

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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE praeparate
                    SET name = %s, wirkstoff = %s, darreichungsform = %s, staerke = %s, einheit = %s, pzn = %s, hersteller = %s
                    WHERE id = %s
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
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write(
            "update_praeparat",
            praeparat_id=praeparat_id,
            name=safe_name,
            wirkstoff=wirkstoff,
            darreichungsform=darreichungsform,
            staerke=staerke,
            einheit=einheit,
            pzn=pzn,
            hersteller=hersteller,
        )
        return changed

    def delete_praeparat(self, praeparat_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS used_count FROM bewegungen WHERE praeparat_id = %s", (int(praeparat_id),))
                used = int(cur.fetchone()["used_count"])
                if used > 0:
                    raise ValueError("Praeparat kann nicht gelöscht werden, da Bewegungen vorhanden sind.")
                cur.execute("DELETE FROM praeparate WHERE id = %s", (int(praeparat_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_praeparat", praeparat_id)
        return changed

    def get_praeparat(self, praeparat_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._dialect.format(sql.SQL_GET_PRAEPARAT),
                    (int(praeparat_id),),
                )
                row = cur.fetchone()
        return dict(row) if row else None
