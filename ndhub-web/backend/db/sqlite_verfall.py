"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteVerfallMixin:
    def _build_verfall_filter_sql(
        self,
        depot_ids: list[int] | None,
        praeparat_ids: list[int] | None,
        search_text: str | None,
        category: str | None,
        critical_days: int,
        warning_days: int,
        attention_days: int,
    ) -> tuple[str, list[Any]]:
        sql = """
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
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
        safe_query = (search_text or "").strip()
        if safe_query:
            like = f"%{safe_query}%"
            sql += """
              AND (
                    d.name LIKE ?
                 OR p.name LIKE ?
                 OR COALESCE(b.charge, '') LIKE ?
                 OR COALESCE(b.verfall, '') LIKE ?
              )
            """
            params.extend([like, like, like, like])

        safe_category = (category or "alle").strip().lower()
        safe_critical_days = max(1, int(critical_days))
        safe_warning_days = max(safe_critical_days + 1, int(warning_days))
        safe_attention_days = max(safe_warning_days + 1, int(attention_days))
        day_expr = "CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER)"
        if safe_category == "kritisch":
            sql += f" AND ({day_expr}) <= ?"
            params.append(safe_critical_days)
        elif safe_category == "warnung":
            sql += f" AND ({day_expr}) > ? AND ({day_expr}) <= ?"
            params.extend([safe_critical_days, safe_warning_days])
        elif safe_category == "achtung":
            sql += f" AND ({day_expr}) > ? AND ({day_expr}) <= ?"
            params.extend([safe_warning_days, safe_attention_days])
        elif safe_category == "abgelaufen":
            sql += f" AND ({day_expr}) < 0"
        return sql, params

    def list_verfall_items(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        search_text: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        safe_offset = max(0, int(offset))
        filter_sql, params = self._build_verfall_filter_sql(
            depot_ids=depot_ids,
            praeparat_ids=praeparat_ids,
            search_text=search_text,
            category=category,
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        query = f"""
            SELECT
                b.id,
                b.depot_id,
                b.praeparat_id,
                d.name AS depot,
                p.name AS praeparat,
                b.charge,
                b.verfall,
                b.anzahl,
                CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER) AS tage_bis_verfall
            {filter_sql}
            ORDER BY date(b.verfall) ASC, d.name ASC, p.name ASC, b.id ASC
            LIMIT ? OFFSET ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params + [safe_limit, safe_offset])).fetchall()
            return [dict(row) for row in rows]

    def count_verfall_items(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        search_text: str | None = None,
        category: str | None = None,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
    ) -> int:
        filter_sql, params = self._build_verfall_filter_sql(
            depot_ids=depot_ids,
            praeparat_ids=praeparat_ids,
            search_text=search_text,
            category=category,
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) {filter_sql}",
                tuple(params),
            ).fetchone()
            return int(row[0] if row else 0)

    def list_new_critical_expiry_events(
        self,
        since_iso: str | None = None,
        limit: int = 25,
        critical_days: int = 30,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        safe_critical_days = max(1, min(int(critical_days), 365))
        since_date = None
        if since_iso:
            text = str(since_iso).strip()
            if text:
                try:
                    since_date = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
                except ValueError:
                    since_date = None
        today = date.today()
        with self._connect() as conn:
            sql = """
                SELECT
                    b.id,
                    d.name AS depot,
                    p.name AS praeparat,
                    b.charge,
                    b.verfall,
                    b.anzahl,
                    date(b.verfall, ?) AS critical_since,
                    CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER) AS tage_bis_verfall
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Zugang'
                  AND COALESCE(b.verfall, '') <> ''
                  AND date(b.verfall) <= date('now', ?)
            """
            params: list[Any] = [f"-{safe_critical_days} day", f"+{safe_critical_days} day"]
            if since_date is not None:
                sql += " AND date(b.verfall, ?) > ?"
                params.extend([f"-{safe_critical_days} day", since_date.isoformat()])
            sql += " ORDER BY date(b.verfall) ASC, b.id ASC LIMIT ?"
            params.append(safe_limit)
            rows = [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

        for row in rows:
            verfall_text = str(row.get("verfall") or "")
            try:
                verfall_day = datetime.strptime(verfall_text, "%Y-%m-%d").date()
                event_day = verfall_day - timedelta(days=safe_critical_days)
                row["event_at"] = datetime.combine(event_day, datetime.min.time(), tzinfo=UTC).isoformat()
            except ValueError:
                row["event_at"] = datetime.combine(today, datetime.min.time(), tzinfo=UTC).isoformat()
        return rows
