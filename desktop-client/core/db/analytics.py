"""Analytics Control Center Queries (Issue #66 / #42).

Insight-Banner, Sparklines, Anomalien, Compliance — LOC-Split aus
``db_manager.Database``. Keine Verhaltensänderung.
"""
from __future__ import annotations

import sqlite3


class AnalyticsMixin:
    """Analytics Control Center SQL (Issue #66 Phase 1).

    Erwartet: ``self.cur``.
    """


    # ─────────────────────────────────────────────────────────────────────
    # Analytics Control Center — neue Query-Methoden (Issue #42, Phase 1)
    # Alle Methoden nutzen parameterized SQL und returnen list[sqlite3.Row]
    # oder list[dict]. Datum-Spalten sind TEXT im Format 'YYYY-MM-DD'.
    # ─────────────────────────────────────────────────────────────────────

    def get_verfall_warnings(self, days: int = 30) -> list[sqlite3.Row]:
        """Präparate, die innerhalb von `days` Tagen verfallen.

        Wird für das Insight-Banner (🚨-Karte) verwendet.
        Liefert depot_name, praeparat_name, charge, verfall, anzahl, depot_id.
        """
        sql = """
            SELECT d.name AS depot_name, d.id AS depot_id,
                   p.name AS praeparat_name, p.id AS praeparat_id,
                   b.charge, b.verfall, b.anzahl
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ = 'Zugang'
              AND b.verfall IS NOT NULL AND b.verfall != ''
              AND date(b.verfall) <= date('now', '+' || ? || ' days')
              AND date(b.verfall) >= date('now')
            ORDER BY b.verfall ASC
        """
        return self.cur.execute(sql, (days,)).fetchall()

    def get_depot_deviation(self) -> list[sqlite3.Row]:
        """Soll/Ist-Abweichung pro Depot (aggregiert).

        Wird für das Insight-Banner (✅-Karte) verwendet.
        Liefert depot_name, depot_id, soll_gesamt, ist_gesamt, differenz.

        Verwendet zwei Subqueries, um JOIN-Kardinalitätsprobleme zu vermeiden
        (sollbestand darf nicht durch mehrere bewegungen-Zeilen multipliziert werden).
        """
        sql = """
            WITH soll AS (
                SELECT dp.depot_id,
                       COALESCE(SUM(dp.sollbestand), 0) AS soll_gesamt
                FROM depot_praeparate dp
                GROUP BY dp.depot_id
            ),
            ist AS (
                SELECT b.depot_id,
                       COALESCE(SUM(CASE
                           WHEN b.typ = 'Zugang' THEN b.anzahl
                           WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                           ELSE 0
                       END), 0) AS ist_gesamt
                FROM bewegungen b
                GROUP BY b.depot_id
            )
            SELECT d.name AS depot_name, d.id AS depot_id,
                   COALESCE(s.soll_gesamt, 0) AS soll_gesamt,
                   COALESCE(i.ist_gesamt, 0) AS ist_gesamt,
                   COALESCE(i.ist_gesamt, 0) - COALESCE(s.soll_gesamt, 0) AS differenz
            FROM depots d
            LEFT JOIN soll s ON s.depot_id = d.id
            LEFT JOIN ist i ON i.depot_id = d.id
            ORDER BY ABS(COALESCE(i.ist_gesamt, 0) - COALESCE(s.soll_gesamt, 0)) DESC
        """
        return self.cur.execute(sql).fetchall()

    def get_inactive_depots(self, days: int = 180) -> list[sqlite3.Row]:
        """Depots ohne Bewegung in den letzten `days` Tagen.

        Wird für das Insight-Banner (⚠️-Karte) verwendet.
        """
        sql = """
            SELECT d.name AS depot_name, d.id AS depot_id,
                   MAX(b.eingang_datum) AS letzte_bewegung
            FROM depots d
            LEFT JOIN bewegungen b ON b.depot_id = d.id
            GROUP BY d.name, d.id
            HAVING letzte_bewegung IS NULL
                OR date(letzte_bewegung) < date('now', '-' || ? || ' days')
            ORDER BY letzte_bewegung ASC NULLS FIRST
        """
        return self.cur.execute(sql, (days,)).fetchall()

    def get_period_trend(self, days: int = 7) -> dict[str, int | float]:
        """Vergleicht aktuelle Periode mit Vorperiode.

        Wird für das Insight-Banner (📈-Karte) verwendet.
        Returnt dict mit zugang_aktuell, zugang_vorperiode, veraenderung_pct.
        """
        sql_aktuell = """
            SELECT COALESCE(SUM(anzahl), 0) FROM bewegungen
            WHERE typ = 'Zugang'
              AND date(eingang_datum) >= date('now', '-' || ? || ' days')
        """
        sql_vorperiode = """
            SELECT COALESCE(SUM(anzahl), 0) FROM bewegungen
            WHERE typ = 'Zugang'
              AND date(eingang_datum) >= date('now', '-' || ? || ' days')
              AND date(eingang_datum) < date('now', '-' || ? || ' days')
        """
        aktuell = self.cur.execute(sql_aktuell, (days,)).fetchone()[0]
        vorperiode = self.cur.execute(sql_vorperiode, (days * 2, days)).fetchone()[0]
        veraenderung_pct = (
            ((aktuell - vorperiode) / vorperiode * 100) if vorperiode > 0 else 0.0
        )
        return {
            "zugang_aktuell": aktuell,
            "zugang_vorperiode": vorperiode,
            "veraenderung_pct": round(veraenderung_pct, 1),
        }

    def get_kpi_sparkline(self, metric: str = "zugang", days: int = 7) -> list[int]:
        """7-Tage-Trend für KPI-Sparklines.

        Args:
            metric: 'zugang' | 'abgang' | 'verfall'
            days: Anzahl Tage für den Trend.

        Returns:
            Liste von Tages-Summen (ältester Tag zuerst).
        """
        if metric == "verfall":
            sql = """
                SELECT date('now', '-' || ? || ' days') AS tag,
                       COALESCE(SUM(anzahl), 0) AS total
                FROM bewegungen
                WHERE typ = 'Zugang' AND date(verfall) = date('now', '-' || ? || ' days')
            """
            # Für Verfall nutzen wir eine andere Logik: Tagesweise Verfall-Summe
            sql = """
                WITH RECURSIVE dates(d) AS (
                    SELECT date('now', '-' || ? || ' days')
                    UNION ALL
                    SELECT date(d, '+1 day') FROM dates WHERE d < date('now')
                )
                SELECT dates.d AS tag,
                       COALESCE((
                           SELECT SUM(b.anzahl) FROM bewegungen b
                           WHERE b.typ = 'Zugang' AND date(b.verfall) = dates.d
                       ), 0) AS total
                FROM dates
                ORDER BY dates.d
            """
            rows = self.cur.execute(sql, (days - 1,)).fetchall()
        else:
            typ_filter = "Zugang" if metric == "zugang" else "Abgang"
            datum_col = "eingang_datum" if metric == "zugang" else "ausgang_datum"
            sql = f"""
                WITH RECURSIVE dates(d) AS (
                    SELECT date('now', '-' || ? || ' days')
                    UNION ALL
                    SELECT date(d, '+1 day') FROM dates WHERE d < date('now')
                )
                SELECT dates.d AS tag,
                       COALESCE((
                           SELECT SUM(b.anzahl) FROM bewegungen b
                           WHERE b.typ = ? AND date(b.{datum_col}) = dates.d
                       ), 0) AS total
                FROM dates
                ORDER BY dates.d
            """
            rows = self.cur.execute(sql, (days - 1, typ_filter)).fetchall()
        return [r[1] for r in rows]

    def get_anomalies(self, threshold_std: float = 2.0) -> list[sqlite3.Row]:
        """Statistische Ausreißer in Bewegungen (Zugang/Abgang).

        Erkennt ungewöhnlich hohe Abgaben oder Zugänge basierend auf
        der Standardabweichung der täglichen Summen pro Präparat.
        """
        sql = """
            WITH daily_totals AS (
                SELECT p.id AS praeparat_id, p.name AS praeparat_name,
                       b.typ, date(b.eingang_datum) AS tag,
                       SUM(b.anzahl) AS total
                FROM bewegungen b
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.eingang_datum IS NOT NULL
                GROUP BY p.id, p.name, b.typ, tag
            ),
            stats AS (
                SELECT praeparat_id, praeparat_name, typ,
                       AVG(total) AS mean,
                       CASE WHEN COUNT(*) > 1 THEN SQRT(AVG(total * total) - AVG(total) * AVG(total))
                            ELSE 0 END AS std
                FROM daily_totals
                GROUP BY praeparat_id, praeparat_name, typ
                HAVING COUNT(*) >= 3
            )
            SELECT dt.praeparat_name, dt.typ, dt.tag, dt.total,
                   ROUND(s.mean, 1) AS mean, ROUND(s.std, 1) AS std,
                   CASE WHEN s.std > 0 THEN ROUND((dt.total - s.mean) / s.std, 2)
                        ELSE 0 END AS z_score
            FROM daily_totals dt
            JOIN stats s ON s.praeparat_id = dt.praeparat_id AND s.typ = dt.typ
            WHERE s.std > 0 AND ABS((dt.total - s.mean) / s.std) >= ?
            ORDER BY ABS((dt.total - s.mean) / s.std) DESC
        """
        return self.cur.execute(sql, (threshold_std,)).fetchall()

    def get_verfall_forecast(self, months: int = 12) -> list[sqlite3.Row]:
        """Verfall-Forecast: monatliche Summe der verfallenden Präparate.

        Liefert monat, verfallende_einheiten, anzahl_chargen für
        die nächsten `months` Monate.
        """
        sql = """
            SELECT strftime('%Y-%m', b.verfall) AS monat,
                   SUM(b.anzahl) AS verfallende_einheiten,
                   COUNT(DISTINCT b.charge) AS anzahl_chargen
            FROM bewegungen b
            WHERE b.typ = 'Zugang'
              AND b.verfall IS NOT NULL AND b.verfall != ''
              AND date(b.verfall) >= date('now')
              AND date(b.verfall) <= date('now', '+' || ? || ' months')
            GROUP BY monat
            ORDER BY monat
        """
        return self.cur.execute(sql, (months,)).fetchall()

    def get_period_comparison(
        self,
        period_a_start: str,
        period_a_end: str,
        period_b_start: str,
        period_b_end: str,
    ) -> dict[str, list[sqlite3.Row] | int]:
        """Vergleicht zwei Zeiträume (für Vergleichs-Modus 'vs. Vorjahr').

        Args:
            Alle Parameter als 'YYYY-MM-DD' Strings.

        Returns:
            dict mit 'period_a', 'period_b' (je liste von rows mit
            depot_name, praeparat_name, typ, summe).
        """
        sql_template = """
            SELECT d.name AS depot_name, p.name AS praeparat_name,
                   b.typ, SUM(b.anzahl) AS summe
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE date(b.eingang_datum) BETWEEN ? AND ?
            GROUP BY d.name, p.name, b.typ
            ORDER BY summe DESC
        """
        period_a = self.cur.execute(sql_template, (period_a_start, period_a_end)).fetchall()
        period_b = self.cur.execute(sql_template, (period_b_start, period_b_end)).fetchall()
        return {"period_a": period_a, "period_b": period_b}

    def get_top_movers(
        self, direction: str = "out", limit: int = 10, days: int = 30
    ) -> list[sqlite3.Row]:
        """Top-Movers: Präparate mit den meisten Zu- oder Abgängen.

        Args:
            direction: 'in' für Zugang, 'out' für Abgang.
            limit: Maximale Anzahl Ergebnisse.
            days: Zeitraum in Tagen.
        """
        if direction not in ("in", "out"):
            msg = "direction must be 'in' or 'out'"
            raise ValueError(msg)
        typ = "Zugang" if direction == "in" else "Abgang"
        datum_col = "eingang_datum" if direction == "in" else "ausgang_datum"
        sql = f"""
            SELECT p.name AS praeparat_name, p.id AS praeparat_id,
                   SUM(b.anzahl) AS gesamt,
                   COUNT(*) AS anzahl_bewegungen,
                   MAX(b.{datum_col}) AS letzte_bewegung
            FROM bewegungen b
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ = ?
              AND b.{datum_col} IS NOT NULL
              AND date(b.{datum_col}) >= date('now', '-' || ? || ' days')
            GROUP BY p.name, p.id
            ORDER BY gesamt DESC
            LIMIT ?
        """
        return self.cur.execute(sql, (typ, days, limit)).fetchall()

    def get_inventory_turnover(self) -> list[sqlite3.Row]:
        """Lagerumschlagshäufigkeit pro Präparat.

        Verhältnis von Abgängen zu durchschnittlichem Bestand.
        Liefert praeparat_name, zugang, abgang, umschlagsrate.
        """
        sql = """
            SELECT p.name AS praeparat_name, p.id AS praeparat_id,
                   COALESCE(SUM(CASE WHEN b.typ = 'Zugang' THEN b.anzahl ELSE 0 END), 0) AS zugang,
                   COALESCE(SUM(CASE WHEN b.typ = 'Abgang' THEN b.anzahl ELSE 0 END), 0) AS abgang,
                   CASE
                       WHEN SUM(CASE WHEN b.typ = 'Zugang' THEN b.anzahl ELSE 0 END) > 0
                       THEN ROUND(
                           CAST(SUM(CASE WHEN b.typ = 'Abgang' THEN b.anzahl ELSE 0 END) AS REAL) /
                           SUM(CASE WHEN b.typ = 'Zugang' THEN b.anzahl ELSE 0 END), 2
                       )
                       ELSE 0
                   END AS umschlagsrate
            FROM praeparate p
            LEFT JOIN bewegungen b ON b.praeparat_id = p.id
            GROUP BY p.name, p.id
            HAVING zugang > 0 OR abgang > 0
            ORDER BY umschlagsrate DESC
        """
        return self.cur.execute(sql).fetchall()

    def get_dead_stock(self, days: int = 180) -> list[sqlite3.Row]:
        """Toter Bestand: Präparate ohne Bewegung in den letzten `days` Tagen.

        Liefert praeparat_name, depot_name, ist_bestand, letzte_bewegung.
        """
        sql = """
            SELECT p.name AS praeparat_name, d.name AS depot_name,
                   COALESCE(SUM(CASE
                       WHEN b.typ = 'Zugang' THEN b.anzahl
                       WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                       ELSE 0
                   END), 0) AS ist_bestand,
                   MAX(b.eingang_datum) AS letzte_bewegung
            FROM depot_praeparate dp
            JOIN praeparate p ON p.id = dp.praeparat_id
            JOIN depots d ON d.id = dp.depot_id
            LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id
                AND b.praeparat_id = dp.praeparat_id
            GROUP BY p.name, d.name
            HAVING ist_bestand > 0
                AND (letzte_bewegung IS NULL
                     OR date(letzte_bewegung) < date('now', '-' || ? || ' days'))
            ORDER BY ist_bestand DESC
        """
        return self.cur.execute(sql, (days,)).fetchall()

    def get_compliance_overview(self) -> dict[str, list[sqlite3.Row]]:
        """Compliance-Übersicht für den Compliance-Tab.

        Liefert Email-Versand-Status und User-Berechtigungs-Übersicht.
        """
        sql_emails = """
            SELECT datum, betreff, empfaenger_depots, empfaenger_emails,
                   anzahl_empfaenger, delivery_status, delivery_channel
            FROM email_verlauf
            ORDER BY datum DESC
            LIMIT 50
        """
        sql_permissions = """
            SELECT u.username, d.name AS depot_name,
                   u.can_read, u.can_write
            FROM user_depot_permissions u
            JOIN depots d ON d.id = u.depot_id
            ORDER BY u.username, d.name
        """
        emails = self.cur.execute(sql_emails).fetchall()
        permissions = self.cur.execute(sql_permissions).fetchall()
        return {"email_verlauf": emails, "permissions": permissions}

    # ─────────────────────────────────────────────────────────────────────
    # Saved Views CRUD (Issue #42 Phase 2)
    # ─────────────────────────────────────────────────────────────────────
