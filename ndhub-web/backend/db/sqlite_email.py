"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteEmailMixin:
    def add_email_verlauf(
        self,
        betreff: str,
        nachricht: str,
        depot_names: str,
        emails: str,
        anzahl: int,
        versand_status: str = "draft",
        versand_kanal: str | None = None,
        versand_fehler: str | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO email_verlauf (
                    datum, betreff, nachricht, empfaenger_depots, empfaenger_emails,
                    anzahl_empfaenger, versand_status, versand_kanal, versand_fehler
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                    (betreff or "").strip(),
                    nachricht or "",
                    depot_names or "",
                    emails or "",
                    int(anzahl),
                    (versand_status or "draft").strip() or "draft",
                    (versand_kanal or "").strip() or None,
                    (versand_fehler or "").strip() or None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_email_verlauf(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id, datum, betreff, empfaenger_depots, anzahl_empfaenger,
                    COALESCE(versand_status, 'draft') AS versand_status,
                    COALESCE(versand_kanal, '') AS versand_kanal
                FROM email_verlauf
                ORDER BY datum DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_email_details(self, email_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id, datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger,
                    COALESCE(versand_status, 'draft') AS versand_status,
                    COALESCE(versand_kanal, '') AS versand_kanal,
                    COALESCE(versand_fehler, '') AS versand_fehler
                FROM email_verlauf
                WHERE id = ?
                """,
                (int(email_id),),
            ).fetchone()
            return dict(row) if row else None

    def update_email_delivery_status(
        self,
        email_id: int,
        versand_status: str,
        versand_kanal: str | None = None,
        versand_fehler: str | None = None,
    ) -> bool:
        safe_status = (versand_status or "").strip().lower()
        if safe_status not in {"draft", "sent", "send_failed"}:
            raise ValueError("Ungueltiger Versandstatus.")
        safe_channel = (versand_kanal or "").strip() or ("manual" if safe_status == "sent" else "draft")
        safe_error = (versand_fehler or "").strip() or None
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE email_verlauf
                SET versand_status = ?,
                    versand_kanal = ?,
                    versand_fehler = ?
                WHERE id = ?
                """,
                (safe_status, safe_channel, safe_error, int(email_id)),
            )
            conn.commit()
            return cur.rowcount > 0
