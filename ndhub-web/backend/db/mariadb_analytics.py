"""MariaDB repository mixins (Issue #110)."""

from __future__ import annotations

import logging
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariadbAnalyticsMixin:
    def get_bewegungen_analyse(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                d.name AS depot,
                p.name AS praeparat,
                b.typ AS typ,
                DATE_FORMAT(COALESCE(b.eingang_datum, b.ausgang_datum), '%%Y-%%m') AS monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) <= %s"
            params.append(end_date)
        sql += " GROUP BY d.name, p.name, b.typ, monat ORDER BY monat, d.name, p.name"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_bestandsentwicklung(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                d.name AS depot,
                p.name AS praeparat,
                dp.sollbestand AS sollbestand,
                COALESCE(SUM(
                    CASE
                        WHEN b.typ = 'Zugang' THEN b.anzahl
                        WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                        ELSE 0
                    END
                ), 0) AS ist_bestand,
                COALESCE(SUM(
                    CASE
                        WHEN b.typ = 'Zugang' THEN b.anzahl
                        WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                        ELSE 0
                    END
                ), 0) - dp.sollbestand AS differenz
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
            WHERE 1=1
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND dp.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND dp.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY d.name, p.name, dp.sollbestand ORDER BY d.name, p.name"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_praeparat_ranking(
        self,
        depot_ids: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                p.name AS name,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ IN ('Abgang', 'Vernichtung')
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= %s"
            params.append(end_date)
        sql += " GROUP BY p.name ORDER BY anzahl DESC LIMIT %s"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_depot_ranking(
        self,
        praeparat_ids: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                d.name AS name,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            WHERE b.typ IN ('Abgang', 'Vernichtung')
        """
        params: list[Any] = []
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= %s"
            params.append(end_date)
        sql += " GROUP BY d.name ORDER BY anzahl DESC LIMIT %s"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_matrix_data(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        d.name AS depot,
                        p.name AS praeparat,
                        dp.sollbestand AS sollbestand,
                        COALESCE(SUM(
                            CASE
                                WHEN b.typ = 'Zugang' THEN b.anzahl
                                WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                                ELSE 0
                            END
                        ), 0) AS ist_bestand
                    FROM depot_praeparate dp
                    JOIN depots d ON d.id = dp.depot_id
                    JOIN praeparate p ON p.id = dp.praeparat_id
                    LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
                    GROUP BY d.name, p.name, dp.sollbestand
                    ORDER BY d.name, p.name
                    """,
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_verfall_prognose(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        horizon_months: int = 24,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                DATE_FORMAT(b.verfall, '%%Y-%%m') AS verfall_monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            WHERE b.typ = 'Zugang'
              AND COALESCE(b.verfall, '') <> ''
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY verfall_monat ORDER BY verfall_monat"
        _ = horizon_months
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_dashboard_overview(
        self,
        limit_activity: int = 8,
        limit_expiry: int = 8,
        critical_days: int = 30,
    ) -> dict[str, Any]:
        safe_activity_limit = max(1, min(int(limit_activity), 50))
        safe_expiry_limit = max(1, min(int(limit_expiry), 50))
        safe_critical_days = max(1, min(int(critical_days), 365))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM depots")
                depot_count = int(cur.fetchone()["c"])
                cur.execute("SELECT COUNT(*) AS c FROM praeparate")
                praeparat_count = int(cur.fetchone()["c"])
                cur.execute("SELECT COUNT(*) AS c FROM bewegungen")
                bewegung_count = int(cur.fetchone()["c"])
                cur.execute(
                    """
                    SELECT COALESCE(SUM(anzahl), 0) AS c
                    FROM bewegungen
                    WHERE typ = 'Zugang'
                      AND COALESCE(verfall, '') <> ''
                      AND DATE(verfall) <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
                    """,
                    (safe_critical_days,),
                )
                kritische_verfaelle = int(cur.fetchone()["c"] or 0)
                cur.execute(
                    """
                    SELECT
                        b.id,
                        b.typ,
                        b.charge,
                        b.verfall,
                        b.anzahl,
                        COALESCE(b.eingang_datum, b.ausgang_datum, '') AS datum,
                        d.name AS depot,
                        p.name AS praeparat
                    FROM bewegungen b
                    JOIN depots d ON d.id = b.depot_id
                    JOIN praeparate p ON p.id = b.praeparat_id
                    ORDER BY b.id DESC
                    LIMIT %s
                    """,
                    (safe_activity_limit,),
                )
                activity_rows = cur.fetchall()
                cur.execute(
                    """
                    SELECT
                        b.id,
                        d.name AS depot,
                        p.name AS praeparat,
                        b.charge,
                        b.verfall,
                        b.anzahl,
                        DATEDIFF(DATE(b.verfall), CURDATE()) AS tage_bis_verfall
                    FROM bewegungen b
                    JOIN depots d ON d.id = b.depot_id
                    JOIN praeparate p ON p.id = b.praeparat_id
                    WHERE b.typ = 'Zugang'
                      AND COALESCE(b.verfall, '') <> ''
                    ORDER BY DATE(b.verfall) ASC, b.id ASC
                    LIMIT %s
                    """,
                    (safe_expiry_limit,),
                )
                expiry_rows = cur.fetchall()
        return {
            "kpis": {
                "depots": depot_count,
                "praeparate": praeparat_count,
                "bewegungen": bewegung_count,
                "kritisch_verfallend": kritische_verfaelle,
            },
            "recent_activity": [dict(row) for row in activity_rows],
            "expiry_preview": [dict(row) for row in expiry_rows],
        }
