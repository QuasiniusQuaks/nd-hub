"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteAnalyticsMixin:
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
                substr(COALESCE(b.eingang_datum, b.ausgang_datum, ''), 1, 7) AS monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) <= ?"
            params.append(end_date)
        sql += " GROUP BY d.name, p.name, b.typ, monat ORDER BY monat, d.name, p.name"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
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
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND dp.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND dp.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY d.name, p.name, dp.sollbestand ORDER BY d.name, p.name"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
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
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= ?"
            params.append(end_date)
        sql += " GROUP BY p.name ORDER BY anzahl DESC LIMIT ?"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
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
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= ?"
            params.append(end_date)
        sql += " GROUP BY d.name ORDER BY anzahl DESC LIMIT ?"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def get_matrix_data(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
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
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_verfall_prognose(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        horizon_months: int = 24,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                substr(b.verfall, 1, 7) AS verfall_monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            WHERE b.typ = 'Zugang'
              AND COALESCE(b.verfall, '') <> ''
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY verfall_monat ORDER BY verfall_monat"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            # horizon_months currently handled in API for portability/readability
            _ = horizon_months
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
            depot_count = int(conn.execute("SELECT COUNT(*) FROM depots").fetchone()[0])
            praeparat_count = int(conn.execute("SELECT COUNT(*) FROM praeparate").fetchone()[0])
            bewegung_count = int(conn.execute("SELECT COUNT(*) FROM bewegungen").fetchone()[0])
            kritische_verfaelle = int(
                conn.execute(
                    """
                    SELECT COALESCE(SUM(anzahl), 0)
                    FROM bewegungen
                    WHERE typ = 'Zugang'
                      AND COALESCE(verfall, '') <> ''
                      AND date(verfall) <= date('now', ?)
                    """,
                    (f"+{safe_critical_days} day",),
                ).fetchone()[0]
                or 0
            )
            activity_rows = conn.execute(
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
                LIMIT ?
                """,
                (safe_activity_limit,),
            ).fetchall()
            expiry_rows = conn.execute(
                """
                SELECT
                    b.id,
                    d.name AS depot,
                    p.name AS praeparat,
                    b.charge,
                    b.verfall,
                    b.anzahl,
                    CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER) AS tage_bis_verfall
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Zugang'
                  AND COALESCE(b.verfall, '') <> ''
                ORDER BY date(b.verfall) ASC, b.id ASC
                LIMIT ?
                """,
                (safe_expiry_limit,),
            ).fetchall()
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
