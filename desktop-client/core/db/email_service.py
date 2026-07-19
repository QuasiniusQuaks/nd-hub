"""SMTP, Email-Verlauf und Analytics-Email-Schedules. Issue #66 Phase 4."""
from __future__ import annotations

import logging
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage

from core.db.constants import DB

logger = logging.getLogger(__name__)


class EmailServiceMixin:
    """Email/SMTP und Schedules. Issue #66 Phase 4.

    Erwartet: ``self.cur``, ``self.conn``, ``get_app_setting``, ``set_app_setting``.
    """

    def add_email_verlauf(
        self,
        betreff,
        nachricht,
        depot_names,
        emails,
        anzahl,
        send_now=False,
        delivery_status="draft",
        delivery_channel="outlook",
        delivery_error=None,
    ):
        datum = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cur.execute("""
            INSERT INTO email_verlauf (
                datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger,
                send_now, delivery_status, delivery_channel, delivery_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datum,
            betreff,
            nachricht,
            depot_names,
            emails,
            anzahl,
            int(bool(send_now)),
            str(delivery_status or "draft"),
            str(delivery_channel or "outlook"),
            str(delivery_error) if delivery_error else None,
        ))
        self.conn.commit()
        return self.cur.lastrowid

    def get_email_verlauf(self, limit=50):
        return self.cur.execute("""
            SELECT id, datum, betreff, empfaenger_depots, anzahl_empfaenger, delivery_status
            FROM email_verlauf
            ORDER BY datum DESC
            LIMIT ?
        """, (limit,)).fetchall()

    def get_email_details(self, email_id):
        return self.cur.execute("""
            SELECT
                datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger,
                send_now, delivery_status, delivery_channel, delivery_error
            FROM email_verlauf
            WHERE id = ?
        """, (email_id,)).fetchone()

    def update_email_verlauf_delivery(self, email_id: int, delivery_status: str, delivery_channel: str, delivery_error: str | None):
        self.cur.execute(
            """
            UPDATE email_verlauf
            SET delivery_status = ?, delivery_channel = ?, delivery_error = ?
            WHERE id = ?
            """,
            (str(delivery_status or "draft"), str(delivery_channel or "outlook"), delivery_error, int(email_id)),
        )
        self.conn.commit()

    def get_smtp_settings(self) -> dict:
        port_raw = self.get_app_setting(DB.SETTING_SMTP_PORT, "587").strip() or "587"
        try:
            port = max(1, min(65535, int(port_raw)))
        except ValueError:
            port = 587
        return {
            "host": self.get_app_setting(DB.SETTING_SMTP_HOST).strip(),
            "port": port,
            "username": self.get_app_setting(DB.SETTING_SMTP_USERNAME).strip(),
            "password": self.get_app_setting(DB.SETTING_SMTP_PASSWORD),
            "use_tls": self.get_app_setting(DB.SETTING_SMTP_USE_TLS, "1").strip().lower() in {"1", "true", "yes", "on"},
            "use_ssl": self.get_app_setting(DB.SETTING_SMTP_USE_SSL, "0").strip().lower() in {"1", "true", "yes", "on"},
            "from_address": self.get_app_setting(DB.SETTING_SMTP_FROM_ADDRESS).strip(),
            "from_name": self.get_app_setting(DB.SETTING_SMTP_FROM_NAME).strip(),
        }

    def save_smtp_settings(self, cfg: dict) -> None:
        self.set_app_setting(DB.SETTING_SMTP_HOST, str(cfg.get("host", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_PORT, str(int(cfg.get("port", 587) or 587)))
        self.set_app_setting(DB.SETTING_SMTP_USERNAME, str(cfg.get("username", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_PASSWORD, str(cfg.get("password", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_USE_TLS, "1" if cfg.get("use_tls") else "0")
        self.set_app_setting(DB.SETTING_SMTP_USE_SSL, "1" if cfg.get("use_ssl") else "0")
        self.set_app_setting(DB.SETTING_SMTP_FROM_ADDRESS, str(cfg.get("from_address", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_FROM_NAME, str(cfg.get("from_name", "") or ""))

    def smtp_settings_missing_for_send(self, cfg: dict | None = None) -> list[str]:
        c = cfg if cfg is not None else self.get_smtp_settings()
        missing: list[str] = []
        if not (c.get("host") or "").strip():
            missing.append("SMTP-Server (Host)")
        if not (c.get("from_address") or "").strip():
            missing.append("Absender-E-Mail")
        if c.get("use_ssl") and c.get("use_tls"):
            missing.append("Nur eine Option: TLS (STARTTLS) oder SSL (SMTPS)")
        return missing

    def send_smtp_email(self, subject: str, message: str, recipients: list[str], cfg: dict | None = None) -> None:
        settings = dict(cfg) if cfg is not None else self.get_smtp_settings()
        missing = self.smtp_settings_missing_for_send(settings)
        if missing:
            raise RuntimeError("SMTP unvollständig: " + ", ".join(missing))
        to_list = [r.strip() for r in recipients if r and str(r).strip()]
        if not to_list:
            raise RuntimeError("Keine Empfänger.")

        msg = EmailMessage()
        msg["Subject"] = (subject or "").strip() or "ND-Hub Nachricht"
        from_addr = (settings.get("from_address") or "").strip()
        from_name = (settings.get("from_name") or "").strip()
        msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"] = ", ".join(to_list)
        msg.set_content(message or "")

        host = (settings.get("host") or "").strip()
        port = int(settings.get("port") or 587)
        use_ssl = bool(settings.get("use_ssl"))
        use_tls = bool(settings.get("use_tls"))
        user = (settings.get("username") or "").strip()
        password = settings.get("password") or ""
        timeout = 15

        try:
            if use_ssl:
                client = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                client = smtplib.SMTP(host, port, timeout=timeout)
            with client as smtp:
                smtp.ehlo()
                if use_tls and not use_ssl:
                    smtp.starttls()
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
                rejected = smtp.send_message(msg) or {}
        except Exception as exc:
            raise RuntimeError(f"SMTP-Versand fehlgeschlagen: {exc}") from exc

        rejected_addrs = sorted(str(a) for a in rejected.keys())
        if len(to_list) - len(rejected_addrs) <= 0:
            raise RuntimeError("SMTP hat keine Empfänger akzeptiert.")

    def test_smtp_connection(self, cfg: dict | None = None) -> tuple[bool, str]:
        settings = dict(cfg) if cfg is not None else self.get_smtp_settings()
        missing = self.smtp_settings_missing_for_send(settings)
        if missing:
            return False, "Unvollständig: " + ", ".join(missing)
        host = (settings.get("host") or "").strip()
        port = int(settings.get("port") or 587)
        use_ssl = bool(settings.get("use_ssl"))
        use_tls = bool(settings.get("use_tls"))
        user = (settings.get("username") or "").strip()
        password = settings.get("password") or ""
        timeout = 12
        try:
            if use_ssl:
                client = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                client = smtplib.SMTP(host, port, timeout=timeout)
            with client as smtp:
                smtp.ehlo()
                if use_tls and not use_ssl:
                    smtp.starttls()
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
        except Exception as exc:
            return False, str(exc)
        return True, "Verbindung und Anmeldung erfolgreich."

    def save_email_schedule(
        self, name: str, recipients: str, schedule: str = "weekly",
        report_type: str = "pdf", enabled: bool = True,
    ) -> bool:
        """Speichert einen Email-Schedule für Analytics-Reports.

        Args:
            name: Name des Schedules.
            recipients: Komma-getrennte Email-Adressen.
            schedule: 'weekly' | 'monthly' | 'daily'.
            report_type: 'pdf' | 'html'.
            enabled: True wenn aktiv.

        Returns:
            True bei Erfolg.
        """
        try:
            self.cur.execute(
                "INSERT INTO analytics_email_schedule (name, recipients, schedule, report_type, enabled) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, recipients, schedule, report_type, 1 if enabled else 0),
            )
            self.conn.commit()
            return True
        except Exception:
            logger.exception("save_email_schedule fehlgeschlagen")
            return False

    def get_email_schedules(self) -> list[sqlite3.Row]:
        """Lädt alle Email-Schedules."""
        return self.cur.execute(
            "SELECT id, name, report_type, recipients, schedule, last_sent, enabled, created_at "
            "FROM analytics_email_schedule ORDER BY created_at DESC"
        ).fetchall()

    def update_email_schedule_sent(self, schedule_id: int) -> bool:
        """Aktualisiert last_sent nach erfolgreichem Versand."""
        self.cur.execute(
            "UPDATE analytics_email_schedule SET last_sent = datetime('now', 'localtime') WHERE id = ?",
            (schedule_id,),
        )
        self.conn.commit()
        return self.cur.rowcount > 0

    def delete_email_schedule(self, schedule_id: int) -> bool:
        """Löscht einen Email-Schedule."""
        self.cur.execute(
            "DELETE FROM analytics_email_schedule WHERE id = ?", (schedule_id,)
        )
        self.conn.commit()
        return self.cur.rowcount > 0

    def toggle_email_schedule(self, schedule_id: int, enabled: bool) -> bool:
        """Aktiviert/Deaktiviert einen Email-Schedule."""
        self.cur.execute(
            "UPDATE analytics_email_schedule SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, schedule_id),
        )
        self.conn.commit()
        return self.cur.rowcount > 0

