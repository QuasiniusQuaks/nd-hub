"""Bewegungen-CRUD und Abfragen. Issue #66 Phase 4."""
from __future__ import annotations

import os
import shutil
from datetime import datetime


class BewegungenMixin:
    """Bewegungen + Attachments + Abgaben-Queries. Issue #66 Phase 4.

    Erwartet: ``self.cur``, ``self.conn``, ``enqueue_sync_change``,
    ``get_depot_id_by_name``, ``get_praeparat_id_by_name``.
    """

    # ----- Bewegungen -----
    def insert_bewegung(self, depot_id, prae_id, charge, verfall, eingang, ausgang, empfaenger, anzahl, typ):
        self.cur.execute("""
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, empfaenger, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (depot_id, prae_id, charge, verfall, eingang, ausgang, empfaenger, anzahl, typ))
        self.conn.commit()

        # Clear caches that depend on movement data
        if hasattr(self.get_all_praeparate_names, 'cache_clear'):
            self.get_all_praeparate_names.cache_clear()
        if hasattr(self.get_all_depot_names, 'cache_clear'):
            self.get_all_depot_names.cache_clear()

        bewegung_id = self.cur.lastrowid
        datum = eingang or ausgang
        depot_name = self.get_depot_name(int(depot_id)) or ""
        praeparat_name = self.get_praeparat_name(int(prae_id)) or ""
        self.enqueue_sync_change(
            entity_name="bewegungen",
            operation="create",
            payload={
                "id": int(bewegung_id),
                "depot_id": int(depot_id),
                "depot_name": depot_name,
                "praeparat_id": int(prae_id),
                "praeparat_name": praeparat_name,
                "typ": typ,
                "charge": charge,
                "verfall": verfall,
                "datum": datum,
                "anzahl": int(anzahl),
                "empfaenger": empfaenger,
            },
        )
        return bewegung_id

    def bulk_insert_bewegungen(self, movements_data):
        """Bulk insert movements for better performance"""
        if not movements_data:
            return []

        # Use executemany for bulk insert
        self.cur.executemany("""
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, empfaenger, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, movements_data)
        self.conn.commit()

        # Clear caches
        if hasattr(self.get_all_praeparate_names, 'cache_clear'):
            self.get_all_praeparate_names.cache_clear()
        if hasattr(self.get_all_depot_names, 'cache_clear'):
            self.get_all_depot_names.cache_clear()

        return [self.cur.lastrowid]

    def list_bewegungen_with_attachments(self, depot_id=None, typ=None, search_text=None):
        sql = """
            SELECT
                b.id, d.name AS depot, p.name AS praeparat, b.typ, b.charge, b.verfall,
                b.eingang_datum, b.ausgang_datum, b.empfaenger, b.anzahl, b.datei_pfad
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params = []
        if depot_id:
            sql += " AND b.depot_id = ?"
            params.append(depot_id)
        if typ and typ != "Alle":
            sql += " AND b.typ = ?"
            params.append(typ)
        if search_text:
            sql += """ AND (
                d.name LIKE ? OR
                p.name LIKE ? OR
                b.typ LIKE ? OR
                b.charge LIKE ? OR
                b.empfaenger LIKE ?
            )"""
            wildcard = f"%{search_text}%"
            params.extend([wildcard] * 5)

        sql += " ORDER BY b.id DESC"
        return self.cur.execute(sql, params).fetchall()

    # ----- Attachments -----
    def link_bewegung_with_attachment(self, bewegung_id: int, local_file_path: str, dest_folder: str, depot_name: str = None):
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Datei nicht gefunden: {local_file_path}")

        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")

        if depot_name:
            safe_depot_name = "".join(c for c in depot_name if c.isalnum() or c in (' ', '_', '-'))
            full_dest = os.path.join(dest_folder, safe_depot_name, year, month)
        else:
            full_dest = os.path.join(dest_folder, year, month)

        os.makedirs(full_dest, exist_ok=True)

        ext = os.path.splitext(local_file_path)[1]
        filename = f"bewegung_{bewegung_id}_{now.strftime('%Y%m%d_%H%M%S')}{ext}"
        dest_path = os.path.join(full_dest, filename)

        shutil.copy2(local_file_path, dest_path)
        self.cur.execute("UPDATE bewegungen SET datei_pfad=? WHERE id=?", (dest_path, bewegung_id))
        self.conn.commit()
        return dest_path

    def get_attachment_for_bewegung(self, bewegung_id: int):
        row = self.cur.execute("SELECT datei_pfad FROM bewegungen WHERE id=?", (bewegung_id,)).fetchone()
        return row[0] if row and row[0] else None

    # ----- Berichte mit Soll/Ist-Vergleich -----
    def query_stock(self, depot_name=None):
        base_sql = """
            WITH v_saldo AS (
                SELECT depot_id, praeparat_id,
                       SUM(CASE WHEN typ='Zugang' THEN anzahl
                           WHEN typ IN ('Abgang','Vernichtung') THEN -anzahl ELSE 0 END) AS saldo
                FROM bewegungen GROUP BY depot_id, praeparat_id
            )
            SELECT
                d.name AS Depot,
                p.name AS Präparat,
                dp.sollbestand AS Soll,
                COALESCE(v.saldo, 0) AS Ist,
                (COALESCE(v.saldo, 0) - dp.sollbestand) AS Differenz
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN v_saldo v ON v.depot_id = dp.depot_id AND v.praeparat_id = dp.praeparat_id
        """
        params = []
        if depot_name and depot_name != "Alle Depots":
            base_sql += " WHERE d.name = ?"
            params.append(depot_name)
        base_sql += " ORDER BY d.name, p.name"
        rows = self.cur.execute(base_sql, params).fetchall()
        return [("Depot", "Präparat", "Soll", "Ist", "Differenz")] + rows

    def query_outgoing(self, year, depot_name=None):
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        sql = """
            SELECT d.name AS Depot, p.name AS Präparat, b.charge AS Charge,
                   b.verfall AS Verfall, b.ausgang_datum AS Ausgang, b.empfaenger AS Empfänger, b.anzahl AS Anzahl
            FROM bewegungen b
            JOIN depots d ON d.id=b.depot_id
            JOIN praeparate p ON p.id=b.praeparat_id
            WHERE b.typ='Abgang' AND b.ausgang_datum >= ? AND b.ausgang_datum <= ?
        """
        params = [start, end]
        if depot_name and depot_name != "Alle Depots":
            sql += " AND d.name = ?"
            params.append(depot_name)
        sql += " ORDER BY d.name, p.name, b.ausgang_datum"
        rows = self.cur.execute(sql, params).fetchall()
        return [("Depot", "Präparat", "Charge", "Verfall", "Ausgang", "Empfänger", "Anzahl")] + rows

    # ----- Statistik-Abfragen -----
    def get_abgaben_by_praeparat(self, praeparat_name, years):
        results = {}
        for year in years:
            start = f"{year}-01-01"
            end = f"{year}-12-31"
            sql = """
                SELECT d.name AS depot, SUM(b.anzahl) AS gesamt
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Abgang'
                  AND p.name = ?
                  AND b.ausgang_datum >= ?
                  AND b.ausgang_datum <= ?
                GROUP BY d.name
                ORDER BY gesamt DESC
            """
            results[year] = self.cur.execute(sql, (praeparat_name, start, end)).fetchall()
        return results

    def get_abgaben_by_depot(self, depot_name, years):
        results = {}
        for year in years:
            start = f"{year}-01-01"
            end = f"{year}-12-31"
            sql = """
                SELECT p.name AS praeparat, SUM(b.anzahl) AS gesamt
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Abgang'
                  AND d.name = ?
                  AND b.ausgang_datum >= ?
                  AND b.ausgang_datum <= ?
                GROUP BY p.name
                ORDER BY gesamt DESC
            """
            results[year] = self.cur.execute(sql, (depot_name, start, end)).fetchall()
        return results

