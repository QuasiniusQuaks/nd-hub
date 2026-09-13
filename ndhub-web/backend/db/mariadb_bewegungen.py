"""MariaDB repository mixins (Issue #110)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariadbBewegungenMixin:
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
        safe_limit = max(1, min(int(limit), 300))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        typ_filter = (typ or "").strip()
        safe_depot_id = int(depot_id) if depot_id is not None else 0
        safe_depot_ids = sorted({int(item) for item in (depot_ids or []) if int(item) > 0})
        safe_praeparat_id = int(praeparat_id) if praeparat_id is not None else 0
        only_with_attachment = bool(has_attachment) if has_attachment is not None else False
        safe_start_date = (start_date or "").strip()
        safe_end_date = (end_date or "").strip()
        ids_filter_sql = ""
        ids_params: tuple[Any, ...] = ()
        if safe_depot_ids:
            placeholders = ",".join("%s" for _ in safe_depot_ids)
            ids_filter_sql = "".join([" AND b.depot_id IN (", placeholders, ")"])
            ids_params = tuple(safe_depot_ids)
        with self._connect() as conn:
            with conn.cursor() as cur:
                sql_parts = [
                    """
                    SELECT
                        b.id,
                        b.depot_id,
                        d.name AS depot_name,
                        b.praeparat_id,
                        p.name AS praeparat_name,
                        b.charge,
                        b.verfall,
                        b.eingang_datum,
                        b.ausgang_datum,
                        b.empfaenger,
                        b.anzahl,
                        b.typ,
                        b.datei_pfad,
                        b.datei_name,
                        b.datei_groesse,
                        b.datei_hochgeladen_am
                    FROM bewegungen b
                    JOIN depots d ON d.id = b.depot_id
                    JOIN praeparate p ON p.id = b.praeparat_id
                    WHERE
                        (%s = '' OR b.typ = %s) AND
                        (%s = 0 OR b.depot_id = %s) AND
                        (%s = 0 OR b.praeparat_id = %s) AND
                        (%s = 0 OR COALESCE(b.datei_pfad, '') <> '') AND
                        (%s = '' OR COALESCE(b.eingang_datum, b.ausgang_datum, '') >= %s) AND
                        (%s = '' OR COALESCE(b.eingang_datum, b.ausgang_datum, '') <= %s) AND
                        (
                            %s = '%%' OR
                            d.name LIKE %s OR
                            p.name LIKE %s OR
                            COALESCE(b.charge, '') LIKE %s OR
                            COALESCE(b.empfaenger, '') LIKE %s
                        )
                    """,
                ]
                if ids_filter_sql:
                    sql_parts.append(ids_filter_sql)
                sql_parts.append("ORDER BY b.id DESC LIMIT %s OFFSET %s")
                cur.execute(
                    "".join(sql_parts),
                    (
                        typ_filter,
                        typ_filter,
                        safe_depot_id,
                        safe_depot_id,
                        safe_praeparat_id,
                        safe_praeparat_id,
                        1 if only_with_attachment else 0,
                        safe_start_date,
                        safe_start_date,
                        safe_end_date,
                        safe_end_date,
                        like,
                        like,
                        like,
                        like,
                        like,
                        *ids_params,
                        safe_limit,
                        safe_offset,
                    ),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_bewegung(self, bewegung_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM bewegungen WHERE id = %s", (int(bewegung_id),))
                row = cur.fetchone()
        return dict(row) if row else None

    def set_bewegung_attachment(self, bewegung_id: int, datei_pfad: str, datei_name: str, datei_groesse: int, datei_hochgeladen_am: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE bewegungen
                    SET datei_pfad = %s,
                        datei_name = %s,
                        datei_groesse = %s,
                        datei_hochgeladen_am = %s
                    WHERE id = %s
                    """,
                    (datei_pfad, datei_name, int(datei_groesse), datei_hochgeladen_am, int(bewegung_id)),
                )
                conn.commit()
        self._mirror_write("set_bewegung_attachment", bewegung_id, datei_pfad, datei_name, datei_groesse, datei_hochgeladen_am)

    def insert_bewegung(
        self,
        depot_id: int,
        praeparat_id: int,
        typ: str,
        charge: str,
        verfall: date | str,
        datum: date | str,
        anzahl: int,
        empfaenger: str | None = None,
    ) -> int:
        movement_type = (typ or "").strip()
        if movement_type not in ALLOWED_MOVEMENT_TYPES:
            raise ValueError("Ungueltiger Bewegungstyp.")
        if int(anzahl) <= 0:
            raise ValueError("Anzahl muss groesser als 0 sein.")

        empfaenger_value = (empfaenger or "").strip() or None
        datum_iso = self._ensure_iso_date(datum)
        verfall_iso = self._ensure_iso_date(verfall)
        eingang_datum = datum_iso if movement_type == "Zugang" else None
        ausgang_datum = datum_iso if movement_type in {"Abgang", "Vernichtung"} else None

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM depots WHERE id = %s", (int(depot_id),))
                if cur.fetchone() is None:
                    raise ValueError("Depot nicht gefunden.")
                cur.execute("SELECT id FROM praeparate WHERE id = %s", (int(praeparat_id),))
                if cur.fetchone() is None:
                    raise ValueError("Praeparat nicht gefunden.")
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM depot_praeparate WHERE depot_id = %s",
                    (int(depot_id),),
                )
                assignment_count = int(cur.fetchone()["cnt"])
                if assignment_count > 0:
                    cur.execute(
                        """
                        SELECT COUNT(*) AS cnt
                        FROM depot_praeparate
                        WHERE depot_id = %s AND praeparat_id = %s
                        """,
                        (int(depot_id), int(praeparat_id)),
                    )
                    if int(cur.fetchone()["cnt"]) == 0:
                        raise ValueError("Praeparat ist diesem Depot nicht zugeordnet.")

                cur.execute(
                    """
                    INSERT INTO bewegungen (
                        depot_id, praeparat_id, charge, verfall,
                        eingang_datum, ausgang_datum, empfaenger, anzahl, typ
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(depot_id),
                        int(praeparat_id),
                        (charge or "").strip(),
                        verfall_iso,
                        eingang_datum,
                        ausgang_datum,
                        empfaenger_value,
                        int(anzahl),
                        movement_type,
                    ),
                )
                conn.commit()
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "insert_bewegung",
            depot_id=depot_id,
            praeparat_id=praeparat_id,
            typ=typ,
            charge=charge,
            verfall=verfall_iso,
            datum=datum_iso,
            anzahl=anzahl,
            empfaenger=empfaenger,
        )
        return new_id
