"""Domain helpers for ND-Hub web backend (Issue #96)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

logger = logging.getLogger(__name__)


try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None
try:
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:  # pragma: no cover
    Workbook = None
    DataValidation = None


from backend.config import EmailDeliverySettings


def _email_delivery_missing_config(settings: EmailDeliverySettings) -> list[str]:
    if settings.mode != "smtp":
        return []
    missing: list[str] = []
    if not settings.smtp_host:
        missing.append("ND_HUB_SMTP_HOST")
    if not settings.smtp_from_address:
        missing.append("ND_HUB_SMTP_FROM_ADDRESS")
    if settings.smtp_use_ssl and settings.smtp_use_tls:
        missing.append("ND_HUB_SMTP_USE_TLS/ND_HUB_SMTP_USE_SSL")
    return missing

def _send_email_via_smtp(
    settings: EmailDeliverySettings,
    subject: str,
    message: str,
    recipients: list[str],
) -> dict[str, Any]:
    if settings.mode != "smtp":
        raise RuntimeError("Live-Versand ist deaktiviert (ND_HUB_EMAIL_DELIVERY_MODE=draft).")
    missing = _email_delivery_missing_config(settings)
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"SMTP-Konfiguration unvollstaendig: {joined}")
    if not recipients:
        raise RuntimeError("Keine Empfaenger vorhanden.")

    msg = EmailMessage()
    msg["Subject"] = (subject or "").strip() or "ND-Hub Nachricht"
    msg["From"] = (
        f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
        if settings.smtp_from_name
        else settings.smtp_from_address
    )
    msg["To"] = ", ".join(recipients)
    msg.set_content(message or "")

    smtp_timeout = max(3, int(settings.smtp_timeout_seconds))
    try:
        if settings.smtp_use_ssl:
            smtp_client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=smtp_timeout)
        else:
            smtp_client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=smtp_timeout)
        with smtp_client as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            rejected = smtp.send_message(msg) or {}
    except Exception as exc:
        raise RuntimeError(f"SMTP-Versand fehlgeschlagen: {exc}") from exc

    rejected_addresses = sorted(str(address) for address in rejected.keys())
    sent_count = max(0, len(recipients) - len(rejected_addresses))
    if sent_count <= 0:
        raise RuntimeError("SMTP hat keine Empfaenger akzeptiert.")
    return {"sent_count": sent_count, "rejected_recipients": rejected_addresses}

