"""Chart-/Auswertungs-Queries für die Desktop-Database (Issue #66).

Ältere Analytics-Methoden (Bestand/Ranking/Matrix) — LOC-Split aus
``db_manager.Database``. Keine Verhaltensänderung.
"""
from __future__ import annotations


class AnalyticsChartsMixin:
    """Chart-Auswertungen (Bewegungen, Ranking, Matrix). Issue #66 Phase 1.

    Erwartet: ``self.cur``.
    """

    def get_bewegungen_analyse(self, depot_ids=None, praeparat_ids=None, start_date=None, end_date=None):
        """Bewegungsanalyse für Diagramme"""
        sql = """
            SELECT
                d.name as depot_name,
                p.name as praeparat_name,
                b.typ,
                strftime('%Y-%m', b.eingang_datum) as monat,
                SUM(b.anzahl) as gesamt
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params = []

        if depot_ids:
            placeholders = ','.join('?' * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(depot_ids)

        if praeparat_ids:
            placeholders = ','.join('?' * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(praeparat_ids)

        if start_date:
            sql += " AND (b.eingang_datum >= ? OR b.ausgang_datum >= ?)"
            params.extend([start_date, start_date])

        if end_date:
            sql += " AND (b.eingang_datum <= ? OR b.ausgang_datum <= ?)"
            params.extend([end_date, end_date])

        sql += " GROUP BY d.name, p.name, b.typ, monat ORDER BY monat"

        return self.cur.execute(sql, params).fetchall()

    def get_bestandsentwicklung(self, depot_ids=None, praeparat_ids=None):
        """Bestandsentwicklung mit Soll/Ist-Vergleich"""
        sql = """
            SELECT
                d.name as depot_name,
                p.name as praeparat_name,
                dp.sollbestand,
                COALESCE(SUM(CASE
                    WHEN b.typ = 'Zugang' THEN b.anzahl
                    WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                    ELSE 0
                END), 0) as ist_bestand,
                COALESCE(SUM(CASE
                    WHEN b.typ = 'Zugang' THEN b.anzahl
                    WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                    ELSE 0
                END), 0) - dp.sollbestand as differenz
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
            WHERE 1=1
        """
        params = []

        if depot_ids:
            placeholders = ','.join('?' * len(depot_ids))
            sql += f" AND dp.depot_id IN ({placeholders})"
            params.extend(depot_ids)

        if praeparat_ids:
            placeholders = ','.join('?' * len(praeparat_ids))
            sql += f" AND dp.praeparat_id IN ({placeholders})"
            params.extend(praeparat_ids)

        sql += " GROUP BY d.name, p.name, dp.sollbestand ORDER BY d.name, p.name"

        return self.cur.execute(sql, params).fetchall()

    def get_depot_ranking(self, praeparat_ids=None, start_date=None, end_date=None, limit=10):
        """Top Depots nach Bewegungen"""
        sql = """
            SELECT
                d.name as depot_name,
                p.name as praeparat_name,
                SUM(CASE WHEN b.typ = 'Abgang' THEN b.anzahl ELSE 0 END) as abgaben_gesamt
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ = 'Abgang'
        """
        params = []

        if praeparat_ids:
            placeholders = ','.join('?' * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(praeparat_ids)

        if start_date:
            sql += " AND b.ausgang_datum >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND b.ausgang_datum <= ?"
            params.append(end_date)

        sql += " GROUP BY d.name, p.name ORDER BY abgaben_gesamt DESC LIMIT ?"
        params.append(limit)

        return self.cur.execute(sql, params).fetchall()

    def get_praeparat_ranking(self, depot_ids=None, start_date=None, end_date=None, limit=10):
        """Top Präparate nach Bewegungen"""
        sql = """
            SELECT
                p.name as praeparat_name,
                d.name as depot_name,
                SUM(CASE WHEN b.typ = 'Abgang' THEN b.anzahl ELSE 0 END) as abgaben_gesamt
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ = 'Abgang'
        """
        params = []

        if depot_ids:
            placeholders = ','.join('?' * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(depot_ids)

        if start_date:
            sql += " AND b.ausgang_datum >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND b.ausgang_datum <= ?"
            params.append(end_date)

        sql += " GROUP BY p.name, d.name ORDER BY abgaben_gesamt DESC LIMIT ?"
        params.append(limit)

        return self.cur.execute(sql, params).fetchall()

    def get_matrix_data(self):
        """Matrix-Daten für Heatmap (Depot × Präparat)"""
        sql = """
            SELECT
                d.name as depot_name,
                p.name as praeparat_name,
                dp.sollbestand,
                COALESCE(SUM(CASE
                    WHEN b.typ = 'Zugang' THEN b.anzahl
                    WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                    ELSE 0
                END), 0) as ist_bestand
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
            GROUP BY d.name, p.name, dp.sollbestand
            ORDER BY d.name, p.name
        """
        return self.cur.execute(sql).fetchall()
