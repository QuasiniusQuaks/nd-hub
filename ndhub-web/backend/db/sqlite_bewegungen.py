"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteBewegungenMixin:
    def list_bewegungen(
        self,
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        typ: str | None = None,
        depot_id: int | None = None,
        depot_ids: list[int] | None = None,
        praeparat_id: int | None = None,
        has_attachment: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        safe_typ = (typ or "").strip()
        safe_depot_id = int(depot_id) if depot_id is not None else 0
        safe_depot_ids = sorted({int(item) for item in (depot_ids or []) if int(item) > 0})
        safe_praeparat_id = int(praeparat_id) if praeparat_id is not None else 0
        only_with_attachment = bool(has_attachment) if has_attachment is not None else False
        safe_start_date = (start_date or "").strip()
        safe_end_date = (end_date or "").strip()
        ids_filter_sql = ""
        ids_params: tuple[Any, ...] = ()
        if safe_depot_ids:
            placeholders = ",".join("?" for _ in safe_depot_ids)
            ids_filter_sql = "".join([" AND depot_id IN (", placeholders, ")"])
            ids_params = tuple(safe_depot_ids)
        with self._connect() as conn:
            sql_parts = [
                """
                SELECT
                    id, depot_id, praeparat_id, typ, charge, verfall,
                    eingang_datum, ausgang_datum, empfaenger, anzahl,
                    datei_name, datei_groesse, datei_hochgeladen_am,
                    CASE WHEN COALESCE(datei_pfad, '') <> '' THEN 1 ELSE 0 END AS has_attachment
                FROM bewegungen
                WHERE (? = '%%' OR
                      COALESCE(charge, '') LIKE ? OR
                      COALESCE(verfall, '') LIKE ? OR
                      COALESCE(empfaenger, '') LIKE ?)
                  AND (? = '' OR typ = ?)
                  AND (? = 0 OR depot_id = ?)
                  AND (? = 0 OR praeparat_id = ?)
                  AND (? = 0 OR COALESCE(datei_pfad, '') <> '')
                  AND (? = '' OR COALESCE(eingang_datum, ausgang_datum, '') >= ?)
                  AND (? = '' OR COALESCE(eingang_datum, ausgang_datum, '') <= ?)
                """,
            ]
            if ids_filter_sql:
                sql_parts.append(ids_filter_sql)
            sql_parts.append("ORDER BY id DESC LIMIT ? OFFSET ?")
            rows = conn.execute(
                "".join(sql_parts),
                (
                    like,
                    like,
                    like,
                    like,
                    safe_typ,
                    safe_typ,
                    safe_depot_id,
                    safe_depot_id,
                    safe_praeparat_id,
                    safe_praeparat_id,
                    1 if only_with_attachment else 0,
                    safe_start_date,
                    safe_start_date,
                    safe_end_date,
                    safe_end_date,
                    *ids_params,
                    safe_limit,
                    safe_offset,
                ),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_bewegung(self, bewegung_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id, depot_id, praeparat_id, typ, charge, verfall,
                    eingang_datum, ausgang_datum, empfaenger, anzahl,
                    datei_pfad, datei_name, datei_groesse, datei_hochgeladen_am
                FROM bewegungen
                WHERE id = ?
                """,
                (int(bewegung_id),),
            ).fetchone()
            return dict(row) if row else None

    def set_bewegung_attachment(
        self,
        bewegung_id: int,
        datei_pfad: str,
        datei_name: str,
        datei_groesse: int,
        uploaded_at: str,
    ) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE bewegungen
                SET datei_pfad = ?, datei_name = ?, datei_groesse = ?, datei_hochgeladen_am = ?
                WHERE id = ?
                """,
                (
                    datei_pfad,
                    datei_name,
                    int(datei_groesse),
                    uploaded_at,
                    int(bewegung_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def insert_bewegung(
        self,
        depot_id: int,
        praeparat_id: int,
        typ: str,
        charge: str,
        verfall: str,
        datum: str,
        anzahl: int,
        empfaenger: str | None = None,
    ) -> int:
        if typ not in ALLOWED_MOVEMENT_TYPES:
            raise ValueError(f"Ungueltiger Typ: {typ}")
        if not charge.strip():
            raise ValueError("Charge darf nicht leer sein.")
        if not verfall.strip():
            raise ValueError("Verfall darf nicht leer sein.")
        if not datum.strip():
            raise ValueError("Datum darf nicht leer sein.")
        if int(anzahl) <= 0:
            raise ValueError("Anzahl muss groesser als 0 sein.")

        eingang = datum if typ == "Zugang" else None
        ausgang = datum if typ in {"Abgang", "Vernichtung"} else None
        empfaenger_value = empfaenger.strip() if empfaenger else None

        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (int(depot_id),),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot existiert nicht.")
            prae_exists = cur.execute(
                "SELECT id FROM praeparate WHERE id = ?",
                (int(praeparat_id),),
            ).fetchone()
            if prae_exists is None:
                raise ValueError("Praeparat existiert nicht.")
            assigned_rows = cur.execute(
                "SELECT praeparat_id FROM depot_praeparate WHERE depot_id = ?",
                (int(depot_id),),
            ).fetchall()
            if assigned_rows:
                assigned_ids = {row["praeparat_id"] for row in assigned_rows}
                if int(praeparat_id) not in assigned_ids:
                    raise ValueError("Praeparat ist diesem Depot nicht zugeordnet.")
            cur.execute(
                """
                INSERT INTO bewegungen (
                    depot_id, praeparat_id, charge, verfall, eingang_datum,
                    ausgang_datum, empfaenger, anzahl, typ
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(depot_id),
                    int(praeparat_id),
                    charge.strip(),
                    verfall.strip(),
                    eingang,
                    ausgang,
                    empfaenger_value,
                    int(anzahl),
                    typ,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
