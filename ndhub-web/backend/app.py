"""FastAPI app for ND-Hub MVP backend."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import re
import shutil
import smtplib
import sqlite3
import tempfile
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode, urlparse
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

logger = logging.getLogger(__name__)

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    import pandas as pd
except ImportError:  # pragma: no cover - optional runtime dependency
    pd = None
try:
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:  # pragma: no cover - optional runtime dependency
    Workbook = None
    DataValidation = None

from backend.auth import (
    SessionInfo,
    TokenStore,
    bearer_scheme,
    get_current_session,
)
from backend.config import (
    EmailDeliverySettings,
    resolve_auto_backup_hours,
    resolve_db_engine,
    resolve_dual_write_sqlite,
    resolve_email_delivery_settings,
    resolve_mariadb_settings,
    resolve_max_backup_restore_mb,
    resolve_runtime_paths,
)
from backend.database import SqliteRepository
from backend.mariadb_repository import MariaDbRepository
from security_manager import SecurityManager


def _require_http_scheme(url: str) -> str:
    """Validates that the URL uses only http/https (SSRF protection)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: Optional[str]
    requires_password_change: bool = False
    permissions: list[str] = Field(default_factory=list)


class DesktopSyncTokenResponse(BaseModel):
    backend_url: str
    token: str
    username: str
    role: Optional[str]
    expires_at: str
    client_label: Optional[str] = None


class DesktopSyncTokenCreateRequest(BaseModel):
    client_label: Optional[str] = Field(default=None, max_length=120)


class DesktopSyncTokenArchiveItem(BaseModel):
    token_fingerprint: str
    token_masked: str
    client_label: Optional[str]
    username: str
    role: Optional[str]
    created_at: str
    expires_at: str
    status: str


class DesktopSyncTokenRevokeRequest(BaseModel):
    token_fingerprint: str = Field(min_length=8)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)
    role: str = Field(min_length=1)
    email: Optional[str] = None
    is_active: bool = True
    permissions: Optional[list[str]] = None


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3)
    role: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[list[str]] = None


class UserPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8)


class BewegungCreateRequest(BaseModel):
    depot_id: int
    praeparat_id: int
    typ: str
    charge: str
    verfall: date
    datum: date
    anzahl: int = Field(gt=0)
    empfaenger: Optional[str] = None


class DepotUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    adresse: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    postleitzahl: Optional[str] = None
    stadt: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    institution_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class InstitutionUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    adresse: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    postleitzahl: Optional[str] = None
    stadt: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class OnboardingPraeparatItem(BaseModel):
    name: str = Field(min_length=1)
    wirkstoff: Optional[str] = None
    darreichungsform: Optional[str] = None
    staerke: Optional[str] = None
    einheit: Optional[str] = None
    pzn: Optional[str] = None
    hersteller: Optional[str] = None


class OnboardingDepotAssignmentItem(BaseModel):
    praeparat_name: str = Field(min_length=1)
    sollbestand: int = Field(ge=0, default=0)


class OnboardingDepotItem(BaseModel):
    name: str = Field(min_length=1)
    adresse: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    postleitzahl: Optional[str] = None
    stadt: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    assignments: list[OnboardingDepotAssignmentItem] = Field(default_factory=list)


class OnboardingInstitutionSetupRequest(BaseModel):
    institution: InstitutionUpsertRequest
    praeparate: list[OnboardingPraeparatItem] = Field(default_factory=list)
    depots: list[OnboardingDepotItem] = Field(default_factory=list)


class UserDepotPermissionItem(BaseModel):
    depot_id: int
    can_read: bool = False
    can_write: bool = False


class UserDepotPermissionUpdateRequest(BaseModel):
    username: str = Field(min_length=1)
    permissions: list[UserDepotPermissionItem] = Field(default_factory=list)


class PraeparatUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    wirkstoff: Optional[str] = None
    darreichungsform: Optional[str] = None
    staerke: Optional[str] = None
    einheit: Optional[str] = None
    pzn: Optional[str] = None
    hersteller: Optional[str] = None


class DepotAssignmentItem(BaseModel):
    praeparat_id: int
    sollbestand: int = Field(ge=0, default=0)


class DepotAssignmentsUpdateRequest(BaseModel):
    assignments: list[DepotAssignmentItem]


class KontaktUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    rolle: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None


class EmailRecipientPreviewRequest(BaseModel):
    depot_ids: list[int] = Field(default_factory=list)
    kontakt_ids: list[int] = Field(default_factory=list)


class EmailDraftCreateRequest(BaseModel):
    depot_ids: list[int] = Field(default_factory=list)
    kontakt_ids: list[int] = Field(default_factory=list)
    betreff: str = Field(min_length=1)
    nachricht: str = ""
    send_now: bool = False


class EmailDeliveryStatusUpdateRequest(BaseModel):
    versand_status: str = Field(min_length=1)
    versand_kanal: Optional[str] = None
    versand_fehler: Optional[str] = None


class SyncPullRequest(BaseModel):
    cursor: Optional[str] = None
    entities: list[str] = Field(default_factory=list)
    limit: int = Field(default=200, ge=1, le=1000)


class SyncPushChangeItem(BaseModel):
    entity: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    client_change_id: Optional[str] = None


class SyncPushRequest(BaseModel):
    batch_id: str = Field(min_length=1, max_length=128)
    changes: list[SyncPushChangeItem] = Field(default_factory=list)


MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}
ALLOWED_IMPORT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
IMPORT_REQUIRED_COLUMNS = ["depot", "praeparat", "typ", "charge", "verfall", "datum", "anzahl"]
IMPORT_COLUMN_ALIASES = {
    "depot": {"depot"},
    "praeparat": {"praeparat", "präparat"},
    "typ": {"typ", "type"},
    "charge": {"charge"},
    "verfall": {"verfall", "verfallsdatum"},
    "datum": {"datum", "date"},
    "anzahl": {"anzahl", "menge", "quantity"},
    "empfaenger": {"empfaenger", "empfänger"},
}


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


def _sanitize_filename_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "")
    return safe.strip("._") or "datei"


def _quote_sql_identifier(name: str) -> str:
    """Quote and validate a SQL identifier (table/column name)."""
    if not name or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(f"Ungueltiger SQL-Bezeichner: {name!r}")
    return f"`{name}`"


def _build_attachment_target_path(
    base_dir: Path,
    bewegung_id: int,
    depot_name: str | None,
    original_name: str,
) -> Path:
    now = datetime.now()
    folder = base_dir / _sanitize_filename_part(depot_name or "depot") / now.strftime("%Y") / now.strftime("%m")
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    stem = _sanitize_filename_part(Path(original_name).stem or "anhang")
    filename = f"bewegung_{bewegung_id}_{timestamp}_{stem}.pdf"
    return folder / filename


def _persist_pdf_upload(upload_file: UploadFile, target: Path) -> int:
    source = upload_file.file
    source.seek(0)
    total_written = 0
    with target.open("wb") as out:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > MAX_ATTACHMENT_SIZE_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise ValueError("PDF-Datei ist zu gross (max. 10 MB).")
            out.write(chunk)
    return total_written


def _normalize_import_column_name(name: str) -> str:
    lowered = (name or "").strip().lower()
    lowered = lowered.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    lowered = re.sub(r"[^a-z0-9]+", "", lowered)
    return lowered


def _parse_id_list_csv(value: str) -> list[int]:
    if not value.strip():
        return []
    result: list[int] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        result.append(int(item))
    return result


def _add_months(iso_date: date, months: int) -> date:
    month_index = (iso_date.year * 12 + iso_date.month - 1) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _normalize_verfall_thresholds(
    critical_days: int = 30,
    warning_days: int = 90,
    attention_days: int = 180,
) -> tuple[int, int, int]:
    critical = max(1, min(int(critical_days), 3650))
    warning = max(critical + 1, min(int(warning_days), 3650))
    attention = max(warning + 1, min(int(attention_days), 3650))
    return critical, warning, attention


def _verfall_category(
    tage_bis_verfall: int,
    critical_days: int,
    warning_days: int,
    attention_days: int,
) -> str:
    if tage_bis_verfall <= critical_days:
        return "kritisch"
    if tage_bis_verfall <= warning_days:
        return "warnung"
    if tage_bis_verfall <= attention_days:
        return "achtung"
    return "ok"


def _enrich_verfall_rows(
    rows: list[dict],
    critical_days: int,
    warning_days: int,
    attention_days: int,
) -> list[dict]:
    enriched: list[dict] = []
    for row in rows:
        item = dict(row)
        try:
            tage = int(item.get("tage_bis_verfall"))
        except (TypeError, ValueError):
            tage = 99999
        item["tage_bis_verfall"] = tage
        item["kategorie"] = _verfall_category(tage, critical_days, warning_days, attention_days)
        enriched.append(item)
    return enriched


def _ensure_import_dependencies() -> None:
    if pd is None:
        raise ValueError("Import-Feature benoetigt pandas. Bitte Abhaengigkeit installieren.")
    if Workbook is None or DataValidation is None:
        raise ValueError("Import-Feature benoetigt openpyxl. Bitte Abhaengigkeit installieren.")


def _load_import_dataframe(upload_file: UploadFile) -> tuple[pd.DataFrame, int]:
    _ensure_import_dependencies()
    filename = (upload_file.filename or "").lower()
    upload_file.file.seek(0)
    if filename.endswith(".csv"):
        df = pd.read_csv(upload_file.file)
        return df, 2
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        upload_file.file.seek(0)
        df = pd.read_excel(upload_file.file, header=2)
        normalized_columns = {_normalize_import_column_name(str(col)) for col in df.columns}
        normalized_required = {
            _normalize_import_column_name(alias)
            for alias in IMPORT_COLUMN_ALIASES["depot"]
        }
        if not normalized_required.intersection(normalized_columns):
            upload_file.file.seek(0)
            df = pd.read_excel(upload_file.file, header=0)
            return df, 2
        return df, 4
    raise ValueError("Nur CSV-, XLSX- oder XLS-Dateien sind erlaubt.")


def _map_import_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for source_col in df.columns:
        normalized = _normalize_import_column_name(str(source_col))
        for target_col, aliases in IMPORT_COLUMN_ALIASES.items():
            normalized_aliases = {_normalize_import_column_name(alias) for alias in aliases}
            if normalized in normalized_aliases:
                rename_map[source_col] = target_col
                break
    mapped = df.rename(columns=rename_map).copy()
    missing = [col for col in IMPORT_REQUIRED_COLUMNS if col not in mapped.columns]
    if missing:
        raise ValueError(f"Fehlende Spalten: {', '.join(missing)}")
    return mapped


def _analyze_import_dataframe(
    repository: SqliteRepository,
    mapped_df: pd.DataFrame,
    row_offset: int,
) -> tuple[list[dict], list[dict], list[str]]:
    working = mapped_df.dropna(how="all").copy()
    if "depot" in working.columns:
        working = working[working["depot"].notna()]
        working = working[working["depot"].astype(str).str.strip() != ""]

    depots = repository.list_depots(limit=10000, offset=0, q="")
    depots_by_name = {str(row["name"]).strip().lower(): int(row["id"]) for row in depots}
    praeparate = repository.list_praeparate(limit=10000, offset=0, q="")
    prae_by_name = {str(row["name"]).strip().lower(): int(row["id"]) for row in praeparate}

    parsed_rows: list[dict] = []
    errors: list[str] = []

    for idx, row in working.iterrows():
        display_row = int(idx) + row_offset
        depot_name = str(row.get("depot", "")).strip()
        prae_name = str(row.get("praeparat", "")).strip()
        typ = str(row.get("typ", "")).strip()
        charge = str(row.get("charge", "")).strip()
        empfaenger_raw = row.get("empfaenger", None)
        empfaenger = str(empfaenger_raw).strip() if pd.notna(empfaenger_raw) else None

        depot_id = depots_by_name.get(depot_name.lower())
        if depot_id is None:
            errors.append(f"Zeile {display_row}: Depot '{depot_name}' nicht gefunden")
            continue
        praeparat_id = prae_by_name.get(prae_name.lower())
        if praeparat_id is None:
            errors.append(f"Zeile {display_row}: Praeparat '{prae_name}' nicht gefunden")
            continue
        if typ not in ALLOWED_IMPORT_TYPES:
            errors.append(f"Zeile {display_row}: Ungueltiger Typ '{typ}'")
            continue
        if not charge:
            errors.append(f"Zeile {display_row}: Charge darf nicht leer sein")
            continue
        try:
            anzahl = int(row.get("anzahl"))
            if anzahl <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            errors.append(f"Zeile {display_row}: Anzahl muss > 0 sein")
            continue
        datum_iso = _parse_import_date(row.get("datum"))
        if datum_iso is None:
            errors.append(f"Zeile {display_row}: Datum ist ungueltig")
            continue
        verfall_iso = _parse_import_date(row.get("verfall"))
        if verfall_iso is None:
            errors.append(f"Zeile {display_row}: Verfall ist ungueltig")
            continue
        parsed_rows.append(
            {
                "display_row": display_row,
                "depot_id": depot_id,
                "praeparat_id": praeparat_id,
                "typ": typ,
                "charge": charge,
                "verfall": verfall_iso,
                "datum": datum_iso,
                "anzahl": anzahl,
                "empfaenger": empfaenger or None,
                "depot": depot_name,
                "praeparat": prae_name,
            }
        )

    preview_rows = working.head(10).fillna("").to_dict(orient="records")
    for row in preview_rows:
        for key, value in row.items():
            row[key] = str(value)
    return parsed_rows, preview_rows, errors


def _parse_import_date(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    value_text = str(value).strip()
    if not value_text:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value_text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    parsed = pd.to_datetime(value_text, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.strftime("%Y-%m-%d")


def _parse_optional_iso_date(value: str, field_name: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} muss YYYY-MM-DD sein.") from exc


def _validated_report_date_range(start_date: str, end_date: str) -> tuple[str | None, str | None]:
    safe_start = _parse_optional_iso_date(start_date, "start_date")
    safe_end = _parse_optional_iso_date(end_date, "end_date")
    if safe_start and safe_end and safe_start > safe_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date darf nicht nach end_date liegen.")
    return safe_start, safe_end


def _safe_report_filename_token(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", (value or "").strip().lower()).strip("_") or "report"


def _build_report_export_filename(
    report_slug: str,
    extension: str,
    perspective: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    horizon_months: int | None = None,
    limit: int | None = None,
) -> str:
    parts = [_safe_report_filename_token(report_slug)]
    safe_perspective = _safe_report_filename_token(perspective or "")
    if safe_perspective and safe_perspective in {"depot", "praeparat"}:
        parts.append(safe_perspective)
    if start_date or end_date:
        start_token = _safe_report_filename_token(start_date or "all")
        end_token = _safe_report_filename_token(end_date or "all")
        parts.append(f"{start_token}_to_{end_token}")
    if horizon_months is not None:
        parts.append(f"h{max(1, int(horizon_months))}m")
    if limit is not None:
        parts.append(f"top{max(1, int(limit))}")
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    safe_extension = _safe_report_filename_token(extension) or "csv"
    return f"{'_'.join(parts)}_{stamp}.{safe_extension}"


def _build_import_execution_fingerprint(filename: str, parsed_rows: list[dict[str, Any]]) -> str:
    canonical_rows: list[dict[str, Any]] = []
    for row in parsed_rows:
        canonical_rows.append(
            {
                "depot_id": int(row.get("depot_id") or 0),
                "praeparat_id": int(row.get("praeparat_id") or 0),
                "typ": str(row.get("typ") or ""),
                "charge": str(row.get("charge") or ""),
                "verfall": str(row.get("verfall") or ""),
                "datum": str(row.get("datum") or ""),
                "anzahl": int(row.get("anzahl") or 0),
                "empfaenger": str(row.get("empfaenger") or ""),
            }
        )
    payload = {
        "filename": str(filename or "").strip().lower(),
        "rows": canonical_rows,
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _classify_import_error_code(error_message: str) -> str:
    text = str(error_message or "").lower()
    if "depot" in text and "nicht gefunden" in text:
        return "unknown_depot"
    if "praeparat" in text and "nicht gefunden" in text:
        return "unknown_praeparat"
    if "ungueltiger typ" in text:
        return "invalid_type"
    if "charge" in text and "leer" in text:
        return "missing_charge"
    if "anzahl" in text:
        return "invalid_amount"
    if "datum" in text:
        return "invalid_date"
    if "verfall" in text:
        return "invalid_expiry"
    if "duplikat" in text:
        return "duplicate"
    return "other"


def _summarize_import_errors(errors: list[str]) -> dict[str, Any]:
    by_code: dict[str, int] = {}
    for item in errors:
        code = _classify_import_error_code(item)
        by_code[code] = by_code.get(code, 0) + 1
    return {"total": int(len(errors)), "by_code": by_code}


def _build_import_template(repository: SqliteRepository) -> bytes:
    _ensure_import_dependencies()
    wb = Workbook()
    ws = wb.active
    ws.title = "Bewegungen"
    depots = [row["name"] for row in repository.list_depots(limit=10000, offset=0, q="")]
    praeparate = [row["name"] for row in repository.list_praeparate(limit=10000, offset=0, q="")]
    typen = ["Zugang", "Abgang", "Vernichtung"]

    validation = wb.create_sheet("Validierung")
    for idx, name in enumerate(depots, start=1):
        validation.cell(row=idx, column=1, value=name)
    for idx, name in enumerate(praeparate, start=1):
        validation.cell(row=idx, column=2, value=name)
    for idx, name in enumerate(typen, start=1):
        validation.cell(row=idx, column=3, value=name)
    validation.sheet_state = "hidden"

    ws.merge_cells("A1:H1")
    ws["A1"] = "Depot in B2 waehlen, danach Daten ab Zeile 4 eintragen."
    ws["A2"] = "Depot:"
    ws["B2"] = depots[0] if depots else ""
    headers = ["Depot", "Praeparat", "Typ", "Charge", "Verfall", "Datum", "Anzahl", "Empfaenger"]
    for col, header in enumerate(headers, start=1):
        ws.cell(row=3, column=col, value=header)
    for row_idx in range(4, 104):
        ws.cell(row=row_idx, column=1, value=f'=IF(B{row_idx}<>"",$B$2,"")')

    if depots:
        dv_depot = DataValidation(type="list", formula1=f"Validierung!$A$1:$A${len(depots)}", allow_blank=False)
        ws.add_data_validation(dv_depot)
        dv_depot.add("B2")
    if praeparate:
        dv_praep = DataValidation(type="list", formula1=f"Validierung!$B$1:$B${len(praeparate)}", allow_blank=False)
        ws.add_data_validation(dv_praep)
        dv_praep.add("B4:B103")
    dv_typ = DataValidation(type="list", formula1=f"Validierung!$C$1:$C${len(typen)}", allow_blank=False)
    ws.add_data_validation(dv_typ)
    dv_typ.add("C4:C103")

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _csv_response(filename: str, headers: list[str], rows: list[list[object]]) -> StreamingResponse:
    text_io = io.StringIO()
    writer = csv.writer(text_io)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    buffer = BytesIO(text_io.getvalue().encode("utf-8"))
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_response(filename: str, title: str, headers: list[str], rows: list[list[object]], kpis: dict) -> StreamingResponse:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PDF-Export erfordert reportlab.") from exc

    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Heading1"]), Spacer(1, 8)]
    if kpis:
        for key, value in kpis.items():
            elements.append(Paragraph(f"<b>{key}:</b> {value}", styles["Normal"]))
        elements.append(Spacer(1, 8))
    table_data = [headers] + rows
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#007aff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pptx_response(filename: str, title: str, headers: list[str], rows: list[list[object]], kpis: dict) -> StreamingResponse:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PPT-Export erfordert python-pptx.") from exc

    prs = Presentation()
    title_slide = prs.slides.add_slide(prs.slide_layouts[5])
    title_box = title_slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.6))
    title_tf = title_box.text_frame
    title_tf.text = title
    title_tf.paragraphs[0].font.size = Pt(24)
    title_tf.paragraphs[0].font.bold = True

    y = 1.0
    if kpis:
        kpi_box = title_slide.shapes.add_textbox(Inches(0.6), Inches(y), Inches(8.8), Inches(1.4))
        kpi_tf = kpi_box.text_frame
        first = True
        for key, value in kpis.items():
            p = kpi_tf.paragraphs[0] if first else kpi_tf.add_paragraph()
            first = False
            p.text = f"{key}: {value}"
            p.font.size = Pt(14)
        y += 1.5

    max_rows = min(len(rows), 18)
    cols = len(headers)
    table_shape = title_slide.shapes.add_table(cols=cols, rows=max_rows + 1, left=Inches(0.4), top=Inches(y), width=Inches(9.0), height=Inches(5.0))
    table = table_shape.table
    for col_idx, header in enumerate(headers):
        table.cell(0, col_idx).text = str(header)
    for r in range(max_rows):
        for c in range(cols):
            table.cell(r + 1, c).text = str(rows[r][c])

    with tempfile.NamedTemporaryFile(suffix=".pptx") as tmp:
        prs.save(tmp.name)
        tmp.seek(0)
        payload = tmp.read()
    out = BytesIO(payload)
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


ALLOWED_USER_ROLES = {"Admin", "User"}
PERMISSION_DEFINITIONS = [
    {"key": "masterdata_read", "label": "Stammdaten lesen"},
    {"key": "masterdata_write", "label": "Stammdaten bearbeiten"},
    {"key": "movements_read", "label": "Bewegungen lesen"},
    {"key": "movements_write", "label": "Bewegungen erfassen"},
    {"key": "settings_read", "label": "Grundeinstellungen lesen"},
    {"key": "settings_write", "label": "Grundeinstellungen bearbeiten"},
    {"key": "import_use", "label": "Import nutzen"},
    {"key": "email_use", "label": "E-Mail nutzen"},
    {"key": "reports_view", "label": "Auswertungen sehen"},
    {"key": "audit_view", "label": "Audit sehen"},
    {"key": "users_manage", "label": "Benutzer verwalten"},
    {"key": "backup_manage", "label": "Backup verwalten"},
]
ALL_PERMISSION_KEYS = {item["key"] for item in PERMISSION_DEFINITIONS}
DEFAULT_USER_PERMISSIONS = {
    "masterdata_read",
    "movements_read",
    "movements_write",
    "settings_read",
    "import_use",
    "email_use",
    "reports_view",
}
PERMISSION_TEMPLATES = [
    {"key": "readonly", "label": "ReadOnly", "permissions": ["masterdata_read", "movements_read", "settings_read", "reports_view"]},
    {"key": "disponent", "label": "Disponent", "permissions": ["masterdata_read", "movements_read", "movements_write", "settings_read", "import_use", "email_use", "reports_view"]},
    {"key": "reporting", "label": "Reporting", "permissions": ["masterdata_read", "movements_read", "reports_view"]},
    {"key": "ops_admin", "label": "Ops Admin", "permissions": ["masterdata_read", "masterdata_write", "movements_read", "movements_write", "settings_read", "settings_write", "import_use", "email_use", "reports_view", "audit_view", "backup_manage"]},
]


def _parse_permission_list(raw_permissions: object) -> set[str]:
    if raw_permissions in (None, ""):
        return set()
    if isinstance(raw_permissions, str):
        try:
            parsed = json.loads(raw_permissions)
        except json.JSONDecodeError:
            return set()
    elif isinstance(raw_permissions, (list, tuple, set)):
        parsed = list(raw_permissions)
    else:
        return set()
    result: set[str] = set()
    for item in parsed:
        key = str(item or "").strip()
        if key in ALL_PERMISSION_KEYS:
            result.add(key)
    return result


def _permissions_for_role(role: str | None, raw_permissions: object) -> set[str]:
    if role == "Admin":
        return set(ALL_PERMISSION_KEYS)
    parsed = _parse_permission_list(raw_permissions)
    return parsed or set(DEFAULT_USER_PERMISSIONS)


def _permissions_json_for_storage(role: str, requested: list[str] | None) -> str:
    allowed = _permissions_for_role(role, requested)
    return json.dumps(sorted(allowed), ensure_ascii=True)


def _normalize_user_row(row: tuple) -> dict:
    effective_permissions = sorted(_permissions_for_role(str(row[2]), row[10] if len(row) > 10 else None))
    return {
        "id": int(row[0]),
        "username": str(row[1]),
        "role": str(row[2]),
        "email": row[3],
        "created_at": row[4],
        "last_login": row[5],
        "is_active": bool(row[6]),
        "failed_attempts": int(row[7] or 0),
        "locked_until": row[8],
        "is_default_password": bool(row[9]),
        "permissions": effective_permissions,
    }


def _get_user_flags(security: SecurityManager, username: str) -> dict[str, bool]:
    row = security.cur.execute(
        "SELECT is_default_password, role, permissions FROM users WHERE username = ?",
        ((username or "").strip(),),
    ).fetchone()
    if not row:
        return {"requires_password_change": False, "permissions": sorted(DEFAULT_USER_PERMISSIONS)}  # nosec B105: boolean flag, not a password
    return {
        "requires_password_change": bool(row[0]),
        "permissions": sorted(_permissions_for_role(str(row[1]), row[2])),
    }


def _get_avatar_path_for_user(security: SecurityManager, username: str) -> Path | None:
    row = security.cur.execute(
        "SELECT avatar_path FROM users WHERE username = ?",
        ((username or "").strip(),),
    ).fetchone()
    if not row or not row[0]:
        return None
    avatar_path = Path(str(row[0])).expanduser()
    if not avatar_path.exists() or not avatar_path.is_file():
        return None
    return avatar_path


def _safe_backup_label(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", (value or "").strip().lower()) or "manual"


def _normalize_json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _parse_iso_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _create_backup_snapshot(source_db_path: Path, backups_dir: Path, label: str) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ndhub_{_safe_backup_label(label)}_{timestamp}.db"
    target_path = backups_dir / filename
    with sqlite3.connect(str(source_db_path)) as source_conn:
        with sqlite3.connect(str(target_path)) as target_conn:
            source_conn.backup(target_conn)
    return target_path


def _create_mariadb_backup_snapshot(backups_dir: Path, label: str) -> Path:
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:
        raise RuntimeError("PyMySQL ist fuer MariaDB-Backups erforderlich.") from exc

    settings = resolve_mariadb_settings()
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ndhub_{_safe_backup_label(label)}_{timestamp}.mariadb.json"
    target_path = backups_dir / filename

    payload: dict[str, object] = {
        "engine": "mariadb",
        "database": settings.database,
        "created_at": datetime.now(UTC).isoformat(),
        "tables": {},
    }
    conn = pymysql.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        database=settings.database,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            rows = cur.fetchall()
            table_names = [str(next(iter(row.values()))) for row in rows]
            table_payload: dict[str, list[dict]] = {}
            for table_name in sorted(table_names):
                quoted_table = _quote_sql_identifier(table_name)
                cur.execute("".join(["SELECT * FROM ", quoted_table]))
                data_rows = []
                for row in cur.fetchall():
                    normalized = {str(k): _normalize_json_value(v) for k, v in dict(row).items()}
                    data_rows.append(normalized)
                table_payload[table_name] = data_rows
            payload["tables"] = table_payload
    finally:
        conn.close()

    with target_path.open("w", encoding="utf-8") as out:
        json.dump(payload, out, ensure_ascii=False)
    return target_path


def _list_backup_files(backups_dir: Path, limit: int = 200) -> list[dict]:
    if not backups_dir.exists():
        return []
    rows: list[dict] = []
    backup_paths = sorted(backups_dir.glob("ndhub_*"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in backup_paths:
        if not path.is_file():
            continue
        if not (
            path.name.endswith(".db")
            or path.name.endswith(".sqlite")
            or path.name.endswith(".sqlite3")
            or path.name.endswith(".mariadb.json")
        ):
            continue
        stat = path.stat()
        rows.append(
            {
                "filename": path.name,
                "size_bytes": int(stat.st_size),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                "kind": "mariadb_json" if path.name.endswith(".mariadb.json") else "sqlite_file",
            }
        )
        if len(rows) >= max(1, min(int(limit), 1000)):
            break
    return rows


def _run_auto_backup_if_due(source_db_path: Path, backups_dir: Path, interval_hours: int) -> Path | None:
    safe_interval_hours = max(1, min(int(interval_hours), 24 * 30))
    now_ts = datetime.now(UTC).timestamp()
    latest_auto_mtime = None
    for path in backups_dir.glob("ndhub_auto_*.db"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if latest_auto_mtime is None or mtime > latest_auto_mtime:
            latest_auto_mtime = mtime
    if latest_auto_mtime is not None:
        elapsed_hours = (now_ts - latest_auto_mtime) / 3600
        if elapsed_hours < safe_interval_hours:
            return None
    return _create_backup_snapshot(source_db_path, backups_dir, "auto")


def _run_auto_backup_if_due_mariadb(backups_dir: Path, interval_hours: int) -> Path | None:
    safe_interval_hours = max(1, min(int(interval_hours), 24 * 30))
    now_ts = datetime.now(UTC).timestamp()
    latest_auto_mtime = None
    for path in backups_dir.glob("ndhub_auto_*.mariadb.json"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if latest_auto_mtime is None or mtime > latest_auto_mtime:
            latest_auto_mtime = mtime
    if latest_auto_mtime is not None:
        elapsed_hours = (now_ts - latest_auto_mtime) / 3600
        if elapsed_hours < safe_interval_hours:
            return None
    return _create_mariadb_backup_snapshot(backups_dir, "auto")


def _restore_mariadb_backup_payload(payload: dict) -> None:
    engine = str(payload.get("engine") or "").strip().lower()
    if engine and engine != "mariadb":
        raise ValueError("Backup-Format ungueltig: engine ist nicht mariadb.")
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("PyMySQL ist fuer MariaDB-Restore erforderlich.") from exc

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Backup-Format ungueltig: 'tables' fehlt.")
    required = {"users", "depots", "praeparate", "bewegungen"}
    present = {str(name) for name in tables.keys()}
    if not required.issubset(present):
        missing = ", ".join(sorted(required - present))
        raise ValueError(f"Backup ungueltig, fehlende Tabellen: {missing}")

    settings = resolve_mariadb_settings()
    conn = pymysql.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        database=settings.database,
        charset="utf8mb4",
        autocommit=False,
    )
    preferred_order = [
        "users",
        "depots",
        "praeparate",
        "depot_praeparate",
        "kontakte",
        "bewegungen",
        "email_verlauf",
        "user_activity_log",
        "api_audit_log",
    ]
    ordered_tables = [name for name in preferred_order if name in tables]
    ordered_tables.extend(name for name in tables.keys() if name not in ordered_tables)

    allowed_restore_tables = set(preferred_order)
    invalid_tables = [name for name in ordered_tables if name not in allowed_restore_tables]
    if invalid_tables:
        raise ValueError(f"Backup enthaelt ungueltige Tabellen: {', '.join(sorted(invalid_tables))}")

    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            for table_name in ordered_tables:
                quoted_table = _quote_sql_identifier(table_name)
                cur.execute("".join(["TRUNCATE TABLE ", quoted_table]))
            for table_name in ordered_tables:
                table_rows = tables.get(table_name) or []
                if not isinstance(table_rows, list) or not table_rows:
                    continue
                first = table_rows[0]
                if not isinstance(first, dict):
                    raise ValueError(f"Backup-Format ungueltig in Tabelle {table_name}.")
                columns = list(first.keys())
                for col in columns:
                    _quote_sql_identifier(col)
                col_sql = ", ".join(_quote_sql_identifier(col) for col in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                query = "".join(
                    [
                        "INSERT INTO ",
                        _quote_sql_identifier(table_name),
                        " (",
                        col_sql,
                        ") VALUES (",
                        placeholders,
                        ")",
                    ]
                )
                values = []
                for row in table_rows:
                    if not isinstance(row, dict):
                        continue
                    values.append(tuple(row.get(col) for col in columns))
                if values:
                    cur.executemany(query, values)
            cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _read_upload_size_bytes(upload_file: UploadFile) -> int:
    upload_file.file.seek(0, io.SEEK_END)
    size_bytes = int(upload_file.file.tell() or 0)
    upload_file.file.seek(0)
    return max(0, size_bytes)


def _validate_restore_upload_size(upload_file: UploadFile, max_bytes: int) -> int:
    size_bytes = _read_upload_size_bytes(upload_file)
    if size_bytes <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup-Datei ist leer.")
    if size_bytes > max_bytes:
        max_mb = round(max_bytes / (1024 * 1024), 2)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Backup-Datei ist zu gross (max. {max_mb} MB).",
        )
    return size_bytes


def _is_valid_sqlite_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            header = handle.read(16)
    except OSError:
        return False
    return header.startswith(b"SQLite format 3")


def create_app(db_path: str | None = None) -> FastAPI:
    """Application factory for runtime and tests."""
    db_engine = resolve_db_engine(default="sqlite")
    runtime_paths = resolve_runtime_paths(db_path=db_path)
    database_path = str(runtime_paths.database_path)
    source_db_path = runtime_paths.database_path
    attachments_dir = runtime_paths.attachments_dir
    backups_dir = runtime_paths.backups_dir
    auto_backup_hours = resolve_auto_backup_hours(default=24)
    max_backup_restore_mb = resolve_max_backup_restore_mb(default=200)
    max_backup_restore_bytes = max_backup_restore_mb * 1024 * 1024
    email_delivery_settings = resolve_email_delivery_settings(default_mode="draft")
    feature_multi_institution = (os.environ.get("ND_HUB_FEATURE_MULTI_INSTITUTION", "1") or "1").strip().lower() in {"1", "true", "yes", "on"}
    feature_institution_map = (os.environ.get("ND_HUB_FEATURE_INSTITUTION_MAP", "1") or "1").strip().lower() in {"1", "true", "yes", "on"}
    sqlite_fallback_repository = SqliteRepository(database_path)
    if db_engine == "mariadb":
        repository = MariaDbRepository(
            settings=resolve_mariadb_settings(),
            fallback=sqlite_fallback_repository,
            dual_write_sqlite=resolve_dual_write_sqlite(default=True),
        )
    else:
        repository = sqlite_fallback_repository
    security = SecurityManager(database_path)
    token_store = TokenStore(storage_path=database_path)

    def _mask_token(token: str) -> str:
        token = str(token or "")
        if len(token) <= 10:
            return "*" * len(token)
        return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"

    def _resolve_archive_status(expires_at: datetime | None, revoked_at: datetime | None, token: str) -> str:
        if isinstance(expires_at, datetime) and expires_at <= datetime.now(UTC):
            return "abgelaufen"
        if revoked_at is not None:
            return "widerrufen"
        return "aktiv" if token_store.get(token) is not None else "widerrufen"

    def _user_permissions(username: str, role: str | None) -> set[str]:
        if role == "Admin":
            return set(ALL_PERMISSION_KEYS)
        row = security.cur.execute(
            "SELECT permissions FROM users WHERE username = ?",
            ((username or "").strip(),),
        ).fetchone()
        raw_permissions = row[0] if row else None
        return _permissions_for_role(role, raw_permissions)

    def _allowed_depot_permissions(session: SessionInfo) -> dict[int, dict[str, bool]]:
        if session.role == "Admin":
            depots = repository.list_depots(limit=2000, offset=0)
            return {
                int(item["id"]): {"can_read": True, "can_write": True}
                for item in depots
                if int(item.get("id", 0)) > 0
            }
        if not hasattr(repository, "list_user_depot_permissions"):
            return {}
        rows = repository.list_user_depot_permissions(session.username)
        result: dict[int, dict[str, bool]] = {}
        for row in rows:
            depot_id = int(row.get("depot_id") or 0)
            if depot_id <= 0:
                continue
            result[depot_id] = {
                "can_read": bool(int(row.get("can_read") or 0)),
                "can_write": bool(int(row.get("can_write") or 0)),
            }
        return result

    def _ensure_depot_access(session: SessionInfo, depot_id: int, require_write: bool = False) -> None:
        if session.role == "Admin":
            return
        allowed = _allowed_depot_permissions(session)
        depot_rights = allowed.get(int(depot_id))
        if not depot_rights:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Depot nicht freigegeben.")
        key = "can_write" if require_write else "can_read"
        if not bool(depot_rights.get(key)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Depot-Berechtigung fehlt.")

    def _allowed_depot_ids(session: SessionInfo, require_write: bool = False) -> list[int]:
        if session.role == "Admin":
            rows = repository.list_depots(limit=5000, offset=0)
            return [int(row["id"]) for row in rows if int(row.get("id", 0)) > 0]
        key = "can_write" if require_write else "can_read"
        allowed = _allowed_depot_permissions(session)
        return sorted([depot_id for depot_id, rights in allowed.items() if rights.get(key)])

    def _scoped_requested_ids(session: SessionInfo, requested_ids: list[int], require_write: bool = False) -> list[int]:
        allowed_ids = set(_allowed_depot_ids(session, require_write=require_write))
        if session.role != "Admin" and not allowed_ids:
            return []
        if not requested_ids:
            return sorted(allowed_ids) if session.role != "Admin" else []
        safe_requested = sorted({int(item) for item in requested_ids if int(item) > 0})
        if session.role == "Admin":
            return safe_requested
        forbidden = [item for item in safe_requested if item not in allowed_ids]
        if forbidden:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mindestens ein Depot ist nicht freigegeben.")
        return safe_requested

    def require_permission(permission_key: str):
        def _dependency(session: SessionInfo = Depends(get_current_session)) -> SessionInfo:
            if permission_key not in ALL_PERMISSION_KEYS:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unbekannte Berechtigung: {permission_key}",
                )
            if session.role == "Admin":
                return session
            permissions = _user_permissions(session.username, session.role)
            if permission_key not in permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Berechtigung fehlt.",
                )
            return session

        return _dependency

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        try:
            try:
                if db_engine == "mariadb":
                    created = _run_auto_backup_if_due_mariadb(backups_dir, auto_backup_hours)
                else:
                    created = _run_auto_backup_if_due(source_db_path, backups_dir, auto_backup_hours)
                if created is not None:
                    repository.log_audit(
                        username="system",
                        action="create",
                        resource_type="backup",
                        details={"operation": "auto", "filename": created.name},
                    )
            except Exception:
                # Auto backup should never block startup.
                logger.warning("Auto-backup during startup failed", exc_info=True)
            yield
        finally:
            security.close()
            token_store.close()

    app = FastAPI(title="ND-Hub Backend", version="0.1.1", lifespan=_lifespan)
    app.state.repository = repository
    app.state.security = security
    app.state.token_store = token_store
    app.state.database_path = database_path
    app.state.web_dir = Path(__file__).parent / "web"
    app.state.attachments_dir = attachments_dir
    app.state.backups_dir = backups_dir
    app.state.auto_backup_hours = auto_backup_hours
    app.state.max_backup_restore_mb = max_backup_restore_mb
    app.state.db_engine = db_engine
    app.state.email_delivery_settings = email_delivery_settings
    app.state.feature_multi_institution = feature_multi_institution
    app.state.feature_institution_map = feature_institution_map

    # ---- Security-Middleware (Fix für #31) ----
    # 1) TrustedHost: blockiert Requests mit unbekanntem Host-Header
    #    (verhindert Host-Header-Injection / Cache-Poisoning).
    #    Default ["*"] = alle Hosts; produktiv bitte ND_HUB_ALLOWED_HOSTS setzen.
    _allowed_hosts_raw = os.environ.get("ND_HUB_ALLOWED_HOSTS", "*").strip()
    if _allowed_hosts_raw == "*":
        _allowed_hosts = ["*"]
    else:
        _allowed_hosts = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

    # 2) CORS: restriktiver Default (allow_origins=[]). Cross-Origin nur
    #    explizit via ND_HUB_CORS_ORIGINS (Komma-getrennte Allowlist).
    _cors_raw = os.environ.get("ND_HUB_CORS_ORIGINS", "").strip()
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # 3) Security-Header-Middleware: schraubt Standard-Schutz-Header auf
    #    jede Response. HSTS nur bei HTTPS-Request, damit Dev über HTTP ok bleibt.
    @app.middleware("http")
    async def _security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response
    # ---- /Security-Middleware ----

    app.mount(
        "/web",
        StaticFiles(directory=app.state.web_dir, html=False),
        name="web",
    )

    @app.get("/")
    def web_index() -> FileResponse:
        return FileResponse(app.state.web_dir / "index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "db_engine": str(app.state.db_engine)}

    @app.post("/auth/login", response_model=LoginResponse)
    def login(payload: LoginRequest) -> LoginResponse:
        ok, _message = security.authenticate(payload.username.strip(), payload.password)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Benutzername oder Passwort ungueltig.",
            )
        username = security.get_current_user() or payload.username
        user_flags = _get_user_flags(security, username)
        token = token_store.issue(
            username=username,
            role=security.get_current_role(),
        )
        return LoginResponse(
            token=token,
            username=username,
            role=security.get_current_role(),
            requires_password_change=user_flags["requires_password_change"],
            permissions=user_flags["permissions"],
        )

    @app.get("/auth/me")
    def auth_me(session: SessionInfo = Depends(get_current_session)) -> dict[str, object]:
        user_flags = _get_user_flags(security, session.username)
        avatar_path = _get_avatar_path_for_user(security, session.username)
        depot_permissions = _allowed_depot_permissions(session)
        return {
            "username": session.username,
            "role": session.role,
            "expires_at": session.expires_at.isoformat(),
            "requires_password_change": user_flags["requires_password_change"],
            "permissions": user_flags["permissions"],
            "avatar_available": avatar_path is not None,
            "depot_permissions": [
                {"depot_id": depot_id, **rights}
                for depot_id, rights in sorted(depot_permissions.items())
            ],
        }

    @app.post("/auth/desktop-sync-token", response_model=DesktopSyncTokenResponse)
    def create_desktop_sync_token(
        request: Request,
        payload: DesktopSyncTokenCreateRequest | None = None,
        session: SessionInfo = Depends(get_current_session),
    ) -> DesktopSyncTokenResponse:
        base_url = str(request.base_url).rstrip("/")
        client_label = str((payload.client_label if payload else "") or "").strip() or None
        desktop_token = token_store.issue(
            username=session.username,
            role=session.role,
            ttl_hours=24 * 365 * 10,
            token_type="desktop_sync",  # nosec B106: token type label, not a password
            token_label=client_label,
        )
        token_info = token_store.get(desktop_token)
        if token_info is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Desktop-Token konnte nicht erzeugt werden.",
            )
        return DesktopSyncTokenResponse(
            backend_url=base_url,
            token=desktop_token,
            username=session.username,
            role=session.role,
            expires_at=token_info.expires_at.isoformat(),
            client_label=client_label,
        )

    @app.get("/auth/desktop-sync-tokens", response_model=list[DesktopSyncTokenArchiveItem])
    def list_desktop_sync_tokens(
        session: SessionInfo = Depends(get_current_session),
    ) -> list[DesktopSyncTokenArchiveItem]:
        _ = session
        rows: list[DesktopSyncTokenArchiveItem] = []
        for entry in token_store.list_tokens(token_type="desktop_sync"):  # nosec B106: token type label, not a password
            issued_at = _parse_iso_datetime(entry.get("issued_at"))
            expires_at = _parse_iso_datetime(entry.get("expires_at"))
            revoked_at = _parse_iso_datetime(entry.get("revoked_at"))
            if not isinstance(issued_at, datetime) or not isinstance(expires_at, datetime):
                continue
            token_value = str(entry.get("token") or "")
            rows.append(
                DesktopSyncTokenArchiveItem(
                    token_fingerprint=str(entry.get("fingerprint") or ""),
                    token_masked=_mask_token(token_value),
                    client_label=entry.get("token_label"),
                    username=str(entry.get("username") or ""),
                    role=entry.get("role"),
                    created_at=issued_at.isoformat(),
                    expires_at=expires_at.isoformat(),
                    status=_resolve_archive_status(expires_at, revoked_at, token_value),
                )
            )
        return rows

    @app.post("/auth/desktop-sync-token/revoke")
    def revoke_desktop_sync_token(
        payload: DesktopSyncTokenRevokeRequest,
        session: SessionInfo = Depends(get_current_session),
    ) -> dict[str, str]:
        _ = session
        revoked = token_store.revoke_by_fingerprint(
            payload.token_fingerprint,
            token_type="desktop_sync",  # nosec B106: token type label, not a password  # nosec B106: token type label, not a password
        )
        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Desktop-Token nicht gefunden oder bereits widerrufen.",
            )
        return {"status": "revoked"}

    @app.get("/permissions/catalog")
    def permissions_catalog(
        session: SessionInfo = Depends(get_current_session),
    ) -> dict:
        _ = session
        return {
            "rows": PERMISSION_DEFINITIONS,
            "default_user_permissions": sorted(DEFAULT_USER_PERMISSIONS),
            "templates": PERMISSION_TEMPLATES,
        }

    @app.get("/onboarding/status")
    def onboarding_status(session: SessionInfo = Depends(require_permission("masterdata_read"))) -> dict:
        _ = session
        if not app.state.feature_multi_institution:
            return {
                "requires_onboarding": False,
                "counts": {"institutions": 0, "depots": 0, "praeparate": 0},
            }
        if hasattr(repository, "get_onboarding_status"):
            status_payload = repository.get_onboarding_status()
            return {
                "requires_onboarding": bool(status_payload.get("requires_onboarding")),
                "counts": status_payload.get("counts") or {},
            }
        depots_rows = repository.list_depots(limit=1, offset=0, q="")
        praeparat_rows = repository.list_praeparate(limit=1, offset=0, q="")
        return {
            "requires_onboarding": len(depots_rows) == 0 or len(praeparat_rows) == 0,
            "counts": {
                "institutions": 0,
                "depots": len(depots_rows),
                "praeparate": len(praeparat_rows),
            },
        }

    @app.post("/onboarding/institution-setup", status_code=status.HTTP_201_CREATED)
    def onboarding_institution_setup(
        payload: OnboardingInstitutionSetupRequest,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict:
        _ = session
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "create_onboarding_setup"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Onboarding nicht verfgbar.")
        try:
            result = repository.create_onboarding_setup(
                institution=payload.institution.model_dump(),
                praeparate=[item.model_dump() for item in payload.praeparate],
                depots=[item.model_dump() for item in payload.depots],
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {
            "status": "created",
            "institution_id": int(result.get("institution_id") or 0),
            "praeparate_count": int(result.get("praeparate_count") or 0),
            "depots": result.get("depots") or [],
        }

    @app.get("/institutions")
    def list_institutions(session: SessionInfo = Depends(require_permission("masterdata_read"))) -> list[dict]:
        _ = session
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "list_institutions"):
            return []
        return repository.list_institutions()

    @app.post("/institutions", status_code=status.HTTP_201_CREATED)
    def create_institution(
        payload: InstitutionUpsertRequest,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "create_institution"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Institutionen nicht verfgbar.")
        try:
            new_id = repository.create_institution(
                name=payload.name,
                adresse=payload.adresse,
                strasse=payload.strasse,
                hausnummer=payload.hausnummer,
                postleitzahl=payload.postleitzahl,
                stadt=payload.stadt,
                latitude=payload.latitude,
                longitude=payload.longitude,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="institution",
            resource_id=new_id,
            details={"name": payload.name},
        )
        return {"id": new_id, "status": "created"}

    @app.put("/institutions/{institution_id}")
    def update_institution(
        institution_id: int,
        payload: InstitutionUpsertRequest,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "update_institution"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Institutionen nicht verfgbar.")
        try:
            changed = repository.update_institution(
                institution_id=institution_id,
                name=payload.name,
                adresse=payload.adresse,
                strasse=payload.strasse,
                hausnummer=payload.hausnummer,
                postleitzahl=payload.postleitzahl,
                stadt=payload.stadt,
                latitude=payload.latitude,
                longitude=payload.longitude,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="institution",
            resource_id=institution_id,
            details={"name": payload.name},
        )
        return {"id": institution_id, "status": "updated"}

    @app.delete("/institutions/{institution_id}")
    def delete_institution(
        institution_id: int,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "delete_institution"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Institutionen nicht verfgbar.")
        try:
            changed = repository.delete_institution(institution_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="institution",
            resource_id=institution_id,
        )
        return {"id": institution_id, "status": "deleted"}

    @app.get("/users/{username}/depot-permissions")
    def get_user_depot_permissions(
        username: str,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> list[dict]:
        _ = session
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "list_user_depot_permissions"):
            return []
        return repository.list_user_depot_permissions(username)

    @app.put("/users/depot-permissions")
    def update_user_depot_permissions(
        payload: UserDepotPermissionUpdateRequest,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> dict[str, str | int]:
        _ = session
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "set_user_depot_permission"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Depot-Rechte nicht verfgbar.")
        for item in payload.permissions:
            repository.set_user_depot_permission(
                username=payload.username,
                depot_id=item.depot_id,
                can_read=item.can_read,
                can_write=item.can_write,
            )
        return {"status": "updated", "count": len(payload.permissions)}

    @app.get("/map/institutions")
    def map_institutions(session: SessionInfo = Depends(require_permission("movements_read"))) -> list[dict]:
        if not app.state.feature_multi_institution or not app.state.feature_institution_map:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "list_map_institutions_with_depots"):
            return []
        rows = repository.list_map_institutions_with_depots()
        if session.role == "Admin":
            return rows
        allowed_ids = set(_allowed_depot_ids(session, require_write=False))
        scoped: list[dict] = []
        for item in rows:
            depots = [depot for depot in item.get("depots", []) if int(depot.get("id") or 0) in allowed_ids]
            if depots:
                copy_item = dict(item)
                copy_item["depots"] = depots
                scoped.append(copy_item)
        return scoped

    @app.get("/geo/geocode")
    def geocode_address(
        q: str,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, float | str]:
        _ = session
        query = (q or "").strip()
        if len(query) < 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adresse zu kurz.")
        try:
            params = urlencode({"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "de"})
            req = UrlRequest(
                _require_http_scheme(f"https://nominatim.openstreetmap.org/search?{params}"),
                headers={"User-Agent": "ndhub-web/geo-geocode"},
            )
            with urlopen(req, timeout=8) as resp:  # nosec B310: URL scheme validated by _require_http_scheme
                payload = json.loads(resp.read().decode("utf-8"))
            if not isinstance(payload, list) or not payload:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keine Koordinate gefunden.")
            top = payload[0] if isinstance(payload[0], dict) else {}
            lat = float(top.get("lat"))
            lon = float(top.get("lon"))
            return {"latitude": lat, "longitude": lon, "display_name": str(top.get("display_name") or "")}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Geokodierung fehlgeschlagen: {exc}") from exc

    @app.get("/auth/activity")
    def auth_activity(
        limit: int = 50,
        session: SessionInfo = Depends(get_current_session),
    ) -> list[dict]:
        safe_limit = max(1, min(int(limit), 200))
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            return []
        rows = security.get_activity_log(user_id=int(user_row[0]), limit=safe_limit)
        result: list[dict] = []
        for row in rows:
            result.append(
                {
                    "id": int(row[0]),
                    "username": str(row[1]),
                    "action": str(row[2]),
                    "details": str(row[3] or ""),
                    "timestamp": str(row[4]),
                }
            )
        return result

    @app.get("/auth/avatar")
    def auth_avatar(
        session: SessionInfo = Depends(get_current_session),
    ) -> FileResponse:
        avatar_path = _get_avatar_path_for_user(security, session.username)
        if avatar_path is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Profilbild vorhanden.")
        return FileResponse(path=avatar_path)

    @app.post("/auth/avatar")
    def upload_auth_avatar(
        file: UploadFile = File(...),
        session: SessionInfo = Depends(get_current_session),
    ) -> dict[str, str]:
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        suffix = Path(filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nur PNG/JPG/JPEG/WEBP/BMP sind erlaubt.",
            )
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            file.file.seek(0)
            shutil.copyfileobj(file.file, tmp)
        try:
            security.current_user = session.username
            security.current_role = session.role
            ok, message = security.set_user_avatar(int(user_row[0]), str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_row[0]),
            details={"change": "avatar_upload"},
        )
        return {"status": "avatar_saved"}

    @app.delete("/auth/avatar")
    def clear_auth_avatar(
        session: SessionInfo = Depends(get_current_session),
    ) -> dict[str, str]:
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        security.current_user = session.username
        security.current_role = session.role
        ok, message = security.clear_user_avatar(int(user_row[0]))
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_row[0]),
            details={"change": "avatar_clear"},
        )
        return {"status": "avatar_cleared"}

    @app.post("/auth/logout")
    def auth_logout(
        session: SessionInfo = Depends(get_current_session),
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> dict[str, str]:
        _ = session
        if credentials and credentials.credentials:
            token_store.revoke(credentials.credentials)
        return {"status": "logged_out"}

    @app.post("/auth/change-password")
    def auth_change_password(
        payload: PasswordChangeRequest,
        session: SessionInfo = Depends(get_current_session),
    ) -> dict[str, str]:
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        ok, message = security.change_password(int(user_row[0]), payload.old_password, payload.new_password)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_row[0]),
            details={"change": "password_self_service"},
        )
        return {"status": "password_changed"}

    @app.get("/users")
    def list_users(
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> list[dict]:
        _ = session
        return [_normalize_user_row(row) for row in security.list_users()]

    @app.get("/users/{user_id}/activity")
    def list_user_activity(
        user_id: int,
        limit: int = 100,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> list[dict]:
        _ = session
        safe_limit = max(1, min(int(limit), 500))
        rows = security.get_activity_log(user_id=int(user_id), limit=safe_limit)
        result: list[dict] = []
        for row in rows:
            result.append(
                {
                    "id": int(row[0]),
                    "username": str(row[1]),
                    "action": str(row[2]),
                    "details": str(row[3] or ""),
                    "timestamp": str(row[4]),
                }
            )
        return result

    @app.post("/users", status_code=status.HTTP_201_CREATED)
    def create_user(
        payload: UserCreateRequest,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> dict:
        _ = session
        safe_username = payload.username.strip()
        if not safe_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benutzername darf nicht leer sein.")
        safe_role = payload.role.strip()
        if safe_role not in ALLOWED_USER_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Rolle.")
        exists = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (safe_username,),
        ).fetchone()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benutzername existiert bereits.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        password_hash = SecurityManager.hash_password(payload.password)
        permissions_json = _permissions_json_for_storage(safe_role, payload.permissions)
        security.cur.execute(
            """
            INSERT INTO users (username, password_hash, role, email, created_at, is_active, is_default_password, permissions)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                safe_username,
                password_hash,
                safe_role,
                (payload.email or "").strip() or None,
                now,
                1 if payload.is_active else 0,
                permissions_json,
            ),
        )
        security.conn.commit()
        user_id = int(security.cur.lastrowid)
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="user",
            resource_id=user_id,
            details={"username": safe_username, "role": safe_role},
        )
        row = security.cur.execute(
            """
            SELECT id, username, role, email, created_at, last_login, is_active, failed_attempts, locked_until, is_default_password, permissions
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        return _normalize_user_row(row)

    @app.put("/users/{user_id}")
    def update_user(
        user_id: int,
        payload: UserUpdateRequest,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> dict:
        _ = session
        row = security.cur.execute(
            "SELECT id, username, role, is_active FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        target_username = str(row[1] or "")
        current_role = str(row[2] or "")
        current_is_active = bool(row[3])
        requested_role = payload.role.strip() if payload.role is not None else current_role
        requested_is_active = bool(payload.is_active) if payload.is_active is not None else current_is_active

        if target_username == session.username:
            if payload.is_active is False:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sie können sich nicht selbst deaktivieren.")
            if payload.role is not None and requested_role != current_role:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sie können Ihre eigene Rolle nicht aendern.")

        # Prevent removing the final active admin via role change or deactivation.
        if current_role == "Admin" and current_is_active and not (requested_role == "Admin" and requested_is_active):
            admin_count = security.cur.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'Admin' AND is_active = 1",
            ).fetchone()[0]
            if int(admin_count) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Letzter aktiver Admin darf nicht herabgestuft oder deaktiviert werden.",
                )
        updates: list[str] = []
        params: list[object] = []
        if payload.username is not None:
            safe_username = payload.username.strip()
            if not safe_username:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benutzername darf nicht leer sein.")
            duplicate = security.cur.execute(
                "SELECT id FROM users WHERE username = ? AND id != ?",
                (safe_username, int(user_id)),
            ).fetchone()
            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benutzername existiert bereits.")
            updates.append("username = ?")
            params.append(safe_username)
        if payload.role is not None:
            safe_role = payload.role.strip()
            if safe_role not in ALLOWED_USER_ROLES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Rolle.")
            updates.append("role = ?")
            params.append(safe_role)
        if payload.email is not None:
            updates.append("email = ?")
            params.append((payload.email or "").strip() or None)
        if payload.permissions is not None:
            effective_role = payload.role.strip() if payload.role else str(row[2])
            updates.append("permissions = ?")
            params.append(_permissions_json_for_storage(effective_role, payload.permissions))
        if payload.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if payload.is_active else 0)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Keine Änderungen angegeben.")
        params.append(int(user_id))
        security.cur.execute(
            "".join(["UPDATE users SET ", ", ".join(updates), " WHERE id = ?"]),
            tuple(params),
        )
        security.conn.commit()
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_id),
            details={"updated_fields": updates},
        )
        refreshed = security.cur.execute(
            """
            SELECT id, username, role, email, created_at, last_login, is_active, failed_attempts, locked_until, is_default_password, permissions
            FROM users
            WHERE id = ?
            """,
            (int(user_id),),
        ).fetchone()
        return _normalize_user_row(refreshed)

    @app.delete("/users/{user_id}")
    def delete_user(
        user_id: int,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> dict[str, int | str]:
        _ = session
        row = security.cur.execute(
            "SELECT id, username, role, is_active FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        if str(row[1]) == session.username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sie können sich nicht selbst löschen.")
        if str(row[2]) == "Admin" and int(row[3]) == 1:
            admin_count = security.cur.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'Admin' AND is_active = 1",
            ).fetchone()[0]
            if int(admin_count) <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Letzter aktiver Admin darf nicht gelöscht werden.")
        security.cur.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
        security.conn.commit()
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="user",
            resource_id=int(user_id),
            details={"username": row[1]},
        )
        return {"id": int(user_id), "status": "deleted"}

    @app.post("/users/{user_id}/reset-password")
    def reset_user_password(
        user_id: int,
        payload: UserPasswordResetRequest,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> dict[str, int | str]:
        _ = session
        row = security.cur.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        new_hash = SecurityManager.hash_password(payload.new_password)
        security.cur.execute(
            """
            UPDATE users
            SET password_hash = ?, failed_attempts = 0, locked_until = NULL, is_default_password = 1
            WHERE id = ?
            """,
            (new_hash, int(user_id)),
        )
        security.conn.commit()
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_id),
            details={"change": "password_reset"},
        )
        return {"id": int(user_id), "status": "password_reset"}

    @app.post("/users/{user_id}/unlock")
    def unlock_user(
        user_id: int,
        session: SessionInfo = Depends(require_permission("users_manage")),
    ) -> dict[str, int | str]:
        _ = session
        row = security.cur.execute(
            "SELECT id FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        security.cur.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
            (int(user_id),),
        )
        security.conn.commit()
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_id),
            details={"change": "unlock"},
        )
        return {"id": int(user_id), "status": "unlocked"}

    @app.get("/admin/backup/list")
    def list_backups(
        limit: int = 200,
        session: SessionInfo = Depends(require_permission("backup_manage")),
    ) -> dict:
        _ = session
        rows = _list_backup_files(backups_dir, limit=limit)
        return {
            "rows": rows,
            "auto_backup_hours": auto_backup_hours,
            "max_restore_size_mb": max_backup_restore_mb,
            "db_engine": db_engine,
        }

    @app.post("/admin/backup/create")
    def create_backup(
        session: SessionInfo = Depends(require_permission("backup_manage")),
    ) -> dict:
        _ = session
        if db_engine == "mariadb":
            backup_path = _create_mariadb_backup_snapshot(backups_dir, "manual")
        else:
            backup_path = _create_backup_snapshot(source_db_path, backups_dir, "manual")
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="backup",
            details={"operation": "manual", "filename": backup_path.name},
        )
        stat = backup_path.stat()
        return {
            "filename": backup_path.name,
            "size_bytes": int(stat.st_size),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        }

    @app.get("/admin/backup/download")
    def download_backup(
        session: SessionInfo = Depends(require_permission("backup_manage")),
    ) -> FileResponse:
        _ = session
        if db_engine == "mariadb":
            backup_path = _create_mariadb_backup_snapshot(backups_dir, "manual")
        else:
            backup_path = _create_backup_snapshot(source_db_path, backups_dir, "manual")
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="backup",
            details={"operation": "manual_download", "filename": backup_path.name},
        )
        return FileResponse(
            path=backup_path,
            filename=backup_path.name,
            media_type="application/octet-stream",
        )

    @app.get("/admin/backup/download/{filename}")
    def download_backup_file(
        filename: str,
        session: SessionInfo = Depends(require_permission("backup_manage")),
    ) -> FileResponse:
        _ = session
        safe_name = Path(filename).name
        backup_path = backups_dir / safe_name
        if not backup_path.exists() or not backup_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup-Datei nicht gefunden.")
        return FileResponse(
            path=backup_path,
            filename=safe_name,
            media_type="application/octet-stream",
        )

    @app.post("/admin/backup/restore")
    def restore_backup(
        file: UploadFile = File(...),
        session: SessionInfo = Depends(require_permission("backup_manage")),
    ) -> dict[str, str]:
        nonlocal security
        nonlocal token_store
        _ = session
        filename = (file.filename or "").strip().lower()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        uploaded_size_bytes = _validate_restore_upload_size(file, max_backup_restore_bytes)
        if db_engine == "mariadb":
            if not filename.endswith((".mariadb.json", ".json")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nur MariaDB-Backup-Dateien mit Endung .mariadb.json/.json sind erlaubt.",
                )
            try:
                file.file.seek(0)
                raw = file.file.read()
                payload = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Backup-Datei konnte nicht gelesen werden: {exc}",
                ) from exc
            pre_restore_path = _create_mariadb_backup_snapshot(backups_dir, "pre_restore")
            try:
                _restore_mariadb_backup_payload(payload)
                security.close()
                security = SecurityManager(database_path)
                app.state.security = security
                token_store = TokenStore()
                app.state.token_store = token_store
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"MariaDB-Restore fehlgeschlagen: {exc}",
                ) from exc
        else:
            if not filename.endswith((".db", ".sqlite", ".sqlite3")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nur Backup-Dateien mit Endung .db/.sqlite/.sqlite3 sind erlaubt.",
                )
            db_target_path = Path(database_path).resolve()
            temp_restore_path = db_target_path.with_name(f"{db_target_path.stem}.restore_tmp{db_target_path.suffix}")
            file.file.seek(0)
            with temp_restore_path.open("wb") as temp_out:
                shutil.copyfileobj(file.file, temp_out)
            if not _is_valid_sqlite_file(temp_restore_path):
                temp_restore_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Backup-Datei ist keine gueltige SQLite-Datei.",
                )
            try:
                with sqlite3.connect(str(temp_restore_path)) as conn:
                    required = {"users", "depots", "praeparate", "bewegungen"}
                    rows = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'",
                    ).fetchall()
                    present = {str(row[0]) for row in rows}
                    if not required.issubset(present):
                        missing = ", ".join(sorted(required - present))
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Backup ungueltig, fehlende Tabellen: {missing}",
                        )
            except HTTPException:
                temp_restore_path.unlink(missing_ok=True)
                raise
            except Exception as exc:
                temp_restore_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Backup-Datei konnte nicht validiert werden: {exc}",
                ) from exc

            pre_restore_path = _create_backup_snapshot(source_db_path, backups_dir, "pre_restore")
            try:
                security.close()
                shutil.move(str(temp_restore_path), str(db_target_path))
                security = SecurityManager(database_path)
                app.state.security = security
                token_store = TokenStore()
                app.state.token_store = token_store
            except Exception as exc:
                temp_restore_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Restore fehlgeschlagen: {exc}",
                ) from exc

        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="backup",
            details={
                "operation": "restore",
                "source_file": filename,
                "source_size_bytes": uploaded_size_bytes,
                "pre_restore_file": pre_restore_path.name,
            },
        )
        return {
            "status": "restored",
            "pre_restore_backup": pre_restore_path.name,
            "message": "Backup erfolgreich wiederhergestellt. Bitte neu anmelden.",
        }

    @app.get("/depots")
    def list_depots(
        q: str = "",
        limit: int = 100,
        offset: int = 0,
        session: SessionInfo = Depends(require_permission("masterdata_read")),
    ) -> list[dict]:
        allowed_ids = list(_allowed_depot_permissions(session).keys()) if session.role != "Admin" else None
        if session.role != "Admin" and not allowed_ids:
            return []
        return repository.list_depots(q=q, limit=limit, offset=offset, allowed_ids=allowed_ids)

    @app.post("/depots", status_code=status.HTTP_201_CREATED)
    def create_depot(
        payload: DepotUpsertRequest,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            new_id = repository.create_depot(
                name=payload.name,
                adresse=payload.adresse,
                strasse=payload.strasse,
                hausnummer=payload.hausnummer,
                postleitzahl=payload.postleitzahl,
                stadt=payload.stadt,
                telefon=payload.telefon,
                email=payload.email,
                institution_id=payload.institution_id,
                latitude=payload.latitude,
                longitude=payload.longitude,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="depot",
            resource_id=new_id,
            details={"name": payload.name},
        )
        return {"id": new_id, "status": "created"}

    @app.put("/depots/{depot_id}")
    def update_depot(
        depot_id: int,
        payload: DepotUpsertRequest,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ensure_depot_access(session, depot_id=depot_id, require_write=True)
        try:
            changed = repository.update_depot(
                depot_id=depot_id,
                name=payload.name,
                adresse=payload.adresse,
                strasse=payload.strasse,
                hausnummer=payload.hausnummer,
                postleitzahl=payload.postleitzahl,
                stadt=payload.stadt,
                telefon=payload.telefon,
                email=payload.email,
                institution_id=payload.institution_id,
                latitude=payload.latitude,
                longitude=payload.longitude,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="depot",
            resource_id=depot_id,
            details={"name": payload.name},
        )
        return {"id": depot_id, "status": "updated"}

    @app.delete("/depots/{depot_id}")
    def delete_depot(
        depot_id: int,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ensure_depot_access(session, depot_id=depot_id, require_write=True)
        try:
            changed = repository.delete_depot(depot_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="depot",
            resource_id=depot_id,
        )
        return {"id": depot_id, "status": "deleted"}

    @app.get("/praeparate")
    def list_praeparate(
        q: str = "",
        limit: int = 100,
        offset: int = 0,
        session: SessionInfo = Depends(require_permission("masterdata_read")),
    ) -> list[dict]:
        _ = session
        return repository.list_praeparate(q=q, limit=limit, offset=offset)

    @app.get("/depots/{depot_id}/praeparate")
    def list_praeparate_for_depot(
        depot_id: int,
        session: SessionInfo = Depends(require_permission("masterdata_read")),
    ) -> list[dict]:
        _ensure_depot_access(session, depot_id=depot_id, require_write=False)
        return repository.list_praeparate_for_depot(depot_id)

    @app.get("/depots/{depot_id}/zuordnungen")
    def list_depot_assignments(
        depot_id: int,
        session: SessionInfo = Depends(require_permission("settings_read")),
    ) -> list[dict]:
        _ensure_depot_access(session, depot_id=depot_id, require_write=False)
        return repository.list_depot_assignments(depot_id)

    @app.put("/depots/{depot_id}/zuordnungen")
    def update_depot_assignments(
        depot_id: int,
        payload: DepotAssignmentsUpdateRequest,
        session: SessionInfo = Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _ensure_depot_access(session, depot_id=depot_id, require_write=True)
        try:
            repository.set_depot_assignments(
                depot_id=depot_id,
                assignments=[item.model_dump() for item in payload.assignments],
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="depot",
            resource_id=depot_id,
            details={"assignments_count": len(payload.assignments)},
        )
        return {"id": depot_id, "status": "assignments_updated"}

    @app.post("/praeparate", status_code=status.HTTP_201_CREATED)
    def create_praeparat(
        payload: PraeparatUpsertRequest,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            new_id = repository.create_praeparat(
                name=payload.name,
                wirkstoff=payload.wirkstoff,
                darreichungsform=payload.darreichungsform,
                staerke=payload.staerke,
                einheit=payload.einheit,
                pzn=payload.pzn,
                hersteller=payload.hersteller,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="praeparat",
            resource_id=new_id,
            details={
                "name": payload.name,
                "wirkstoff": payload.wirkstoff,
                "darreichungsform": payload.darreichungsform,
                "staerke": payload.staerke,
                "einheit": payload.einheit,
                "pzn": payload.pzn,
                "hersteller": payload.hersteller,
            },
        )
        return {"id": new_id, "status": "created"}

    @app.put("/praeparate/{praeparat_id}")
    def update_praeparat(
        praeparat_id: int,
        payload: PraeparatUpsertRequest,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            changed = repository.update_praeparat(
                praeparat_id=praeparat_id,
                name=payload.name,
                wirkstoff=payload.wirkstoff,
                darreichungsform=payload.darreichungsform,
                staerke=payload.staerke,
                einheit=payload.einheit,
                pzn=payload.pzn,
                hersteller=payload.hersteller,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Praeparat nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="praeparat",
            resource_id=praeparat_id,
            details={
                "name": payload.name,
                "wirkstoff": payload.wirkstoff,
                "darreichungsform": payload.darreichungsform,
                "staerke": payload.staerke,
                "einheit": payload.einheit,
                "pzn": payload.pzn,
                "hersteller": payload.hersteller,
            },
        )
        return {"id": praeparat_id, "status": "updated"}

    @app.delete("/praeparate/{praeparat_id}")
    def delete_praeparat(
        praeparat_id: int,
        session: SessionInfo = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            changed = repository.delete_praeparat(praeparat_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Praeparat nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="praeparat",
            resource_id=praeparat_id,
        )
        return {"id": praeparat_id, "status": "deleted"}

    @app.get("/depots/{depot_id}/kontakte")
    def list_kontakte_for_depot(
        depot_id: int,
        session: SessionInfo = Depends(require_permission("settings_read")),
    ) -> list[dict]:
        _ensure_depot_access(session, depot_id=depot_id, require_write=False)
        return repository.list_kontakte(depot_id)

    @app.post("/depots/{depot_id}/kontakte", status_code=status.HTTP_201_CREATED)
    def create_kontakt_for_depot(
        depot_id: int,
        payload: KontaktUpsertRequest,
        session: SessionInfo = Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _ensure_depot_access(session, depot_id=depot_id, require_write=True)
        try:
            kontakt_id = repository.create_kontakt(
                depot_id=depot_id,
                name=payload.name,
                rolle=payload.rolle,
                telefon=payload.telefon,
                email=payload.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="kontakt",
            resource_id=kontakt_id,
            details={"depot_id": depot_id, "name": payload.name},
        )
        return {"id": kontakt_id, "status": "created"}

    @app.put("/kontakte/{kontakt_id}")
    def update_kontakt(
        kontakt_id: int,
        payload: KontaktUpsertRequest,
        session: SessionInfo = Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            changed = repository.update_kontakt(
                kontakt_id=kontakt_id,
                name=payload.name,
                rolle=payload.rolle,
                telefon=payload.telefon,
                email=payload.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kontakt nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="kontakt",
            resource_id=kontakt_id,
            details={"name": payload.name},
        )
        return {"id": kontakt_id, "status": "updated"}

    @app.delete("/kontakte/{kontakt_id}")
    def delete_kontakt(
        kontakt_id: int,
        session: SessionInfo = Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _ = session
        changed = repository.delete_kontakt(kontakt_id)
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kontakt nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="kontakt",
            resource_id=kontakt_id,
        )
        return {"id": kontakt_id, "status": "deleted"}

    @app.post("/emails/recipients-preview")
    def preview_email_recipients(
        payload: EmailRecipientPreviewRequest,
        session: SessionInfo = Depends(require_permission("email_use")),
    ) -> dict:
        _ = session
        if not payload.depot_ids:
            return {"count": 0, "recipients": [], "depot_names": [], "selected_contact_count": 0}
        recipients = repository.get_kontakte_by_depot_ids(payload.depot_ids)
        selected_contact_count = 0
        if payload.kontakt_ids:
            selected_ids = {int(item) for item in payload.kontakt_ids if int(item) > 0}
            selected_contact_count = len(selected_ids)
            recipients = [row for row in recipients if int(row.get("id") or 0) in selected_ids]
        depot_names = sorted({str(row["depot_name"]) for row in recipients})
        return {
            "count": len(recipients),
            "recipients": recipients,
            "depot_names": depot_names,
            "selected_contact_count": selected_contact_count,
        }

    @app.get("/emails/delivery/status")
    def get_email_delivery_status(
        session: SessionInfo = Depends(require_permission("email_use")),
    ) -> dict[str, Any]:
        _ = session
        settings = app.state.email_delivery_settings
        missing = _email_delivery_missing_config(settings)
        return {
            "mode": settings.mode,
            "can_send_now": settings.mode == "smtp" and not missing,
            "from_address": settings.smtp_from_address,
            "from_name": settings.smtp_from_name,
            "missing_config": missing,
        }

    @app.post("/emails/drafts", status_code=status.HTTP_201_CREATED)
    def create_email_draft(
        payload: EmailDraftCreateRequest,
        session: SessionInfo = Depends(require_permission("email_use")),
    ) -> dict[str, Any]:
        _ = session
        if not payload.depot_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bitte mindestens ein Depot auswaehlen.")
        recipients = repository.get_kontakte_by_depot_ids(payload.depot_ids)
        if payload.kontakt_ids:
            selected_ids = {int(item) for item in payload.kontakt_ids if int(item) > 0}
            recipients = [row for row in recipients if int(row.get("id") or 0) in selected_ids]
        if not recipients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fuer die ausgewaehlten Depots sind keine Ansprechpartner mit E-Mail hinterlegt.",
            )
        emails = [str(row["email"]).strip() for row in recipients if str(row.get("email", "")).strip()]
        unique_emails = sorted(set(emails))
        depot_names = sorted({str(row["depot_name"]) for row in recipients})
        send_now_requested = bool(payload.send_now)
        delivery_status = "draft"
        delivery_error = ""
        smtp_result: dict[str, Any] = {}
        if send_now_requested:
            try:
                smtp_result = _send_email_via_smtp(
                    app.state.email_delivery_settings,
                    subject=payload.betreff,
                    message=payload.nachricht or "",
                    recipients=unique_emails,
                )
                delivery_status = "sent"
            except RuntimeError as exc:
                delivery_status = "send_failed"
                delivery_error = str(exc)
        log_id = repository.add_email_verlauf(
            betreff=payload.betreff,
            nachricht=payload.nachricht or "",
            depot_names=", ".join(depot_names),
            emails="; ".join(unique_emails),
            anzahl=len(unique_emails),
            versand_status=delivery_status,
            versand_kanal="smtp" if delivery_status == "sent" else "draft",
            versand_fehler=delivery_error or None,
        )
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="email",
            resource_id=log_id,
            details={
                "depot_ids": payload.depot_ids,
                "kontakt_ids": payload.kontakt_ids,
                "recipient_count": len(unique_emails),
                "send_now_requested": send_now_requested,
                "delivery_status": delivery_status,
                "delivery_error": delivery_error or None,
            },
        )
        return {
            "id": log_id,
            "status": "draft_created",
            "recipient_count": len(unique_emails),
            "delivery_status": delivery_status,
            "delivery_error": delivery_error or None,
            "sent_count": int(smtp_result.get("sent_count") or 0),
            "rejected_recipients": smtp_result.get("rejected_recipients") or [],
        }

    @app.get("/emails/history")
    def list_email_history(
        limit: int = 50,
        session: SessionInfo = Depends(require_permission("email_use")),
    ) -> list[dict]:
        _ = session
        return repository.get_email_verlauf(limit=limit)

    @app.get("/emails/history/{email_id}")
    def get_email_history_detail(
        email_id: int,
        session: SessionInfo = Depends(require_permission("email_use")),
    ) -> dict:
        _ = session
        details = repository.get_email_details(email_id)
        if details is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-Mail-Eintrag nicht gefunden.")
        return details

    @app.patch("/emails/history/{email_id}/delivery-status")
    def update_email_history_delivery_status(
        email_id: int,
        payload: EmailDeliveryStatusUpdateRequest,
        session: SessionInfo = Depends(require_permission("email_use")),
    ) -> dict[str, Any]:
        _ = session
        current = repository.get_email_details(email_id)
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-Mail-Eintrag nicht gefunden.")
        try:
            changed = repository.update_email_delivery_status(
                email_id=email_id,
                versand_status=payload.versand_status,
                versand_kanal=payload.versand_kanal,
                versand_fehler=payload.versand_fehler,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-Mail-Eintrag nicht gefunden.")
        updated = repository.get_email_details(email_id) or {}
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="email",
            resource_id=email_id,
            details={
                "versand_status": updated.get("versand_status"),
                "versand_kanal": updated.get("versand_kanal"),
                "versand_fehler": updated.get("versand_fehler"),
            },
        )
        return {"id": email_id, "status": "updated", "delivery": updated}

    @app.get("/bewegungen")
    def list_bewegungen(
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        typ: str = "",
        depot_id: int = 0,
        praeparat_id: int = 0,
        has_attachment: int = 0,
        start_date: str = "",
        end_date: str = "",
        session: SessionInfo = Depends(require_permission("movements_read")),
    ) -> list[dict]:
        scoped_ids = _scoped_requested_ids(
            session,
            [int(depot_id)] if int(depot_id or 0) > 0 else [],
            require_write=False,
        )
        if session.role != "Admin" and not scoped_ids:
            return []
        requested_depot_id = int(depot_id) if int(depot_id or 0) > 0 else None
        depot_scope_ids = scoped_ids if session.role != "Admin" else []
        rows = repository.list_bewegungen(
            limit=limit,
            offset=offset,
            q=q,
            typ=typ or None,
            depot_id=requested_depot_id,
            depot_ids=depot_scope_ids or None,
            praeparat_id=praeparat_id if int(praeparat_id or 0) > 0 else None,
            has_attachment=bool(int(has_attachment or 0)),
            start_date=start_date or None,
            end_date=end_date or None,
        )
        return rows

    @app.get("/bewegungen/export.csv")
    def export_bewegungen_csv(
        q: str = "",
        typ: str = "",
        depot_id: int = 0,
        praeparat_id: int = 0,
        has_attachment: int = 0,
        start_date: str = "",
        end_date: str = "",
        session: SessionInfo = Depends(require_permission("movements_read")),
    ) -> StreamingResponse:
        requested_depot_id = depot_id if int(depot_id or 0) > 0 else None
        if requested_depot_id is not None and session.role != "Admin":
            _ensure_depot_access(session, depot_id=requested_depot_id, require_write=False)
        rows = repository.list_bewegungen(
            limit=5000,
            offset=0,
            q=q,
            typ=typ or None,
            depot_id=requested_depot_id,
            depot_ids=_scoped_requested_ids(
                session,
                [int(depot_id)] if int(depot_id or 0) > 0 else [],
                require_write=False,
            ) if session.role != "Admin" else None,
            praeparat_id=praeparat_id if int(praeparat_id or 0) > 0 else None,
            has_attachment=bool(int(has_attachment or 0)),
            start_date=start_date or None,
            end_date=end_date or None,
        )
        headers = [
            "ID",
            "Typ",
            "Charge",
            "Verfall",
            "Datum",
            "Anzahl",
            "Depot_ID",
            "Praeparat_ID",
            "Empfaenger",
            "Hat_PDF",
            "Datei",
        ]
        data_rows = []
        for row in rows:
            datum = row.get("eingang_datum") or row.get("ausgang_datum") or ""
            has_pdf = int(row.get("has_attachment") or 0)
            data_rows.append(
                [
                    row.get("id", ""),
                    row.get("typ", ""),
                    row.get("charge", ""),
                    row.get("verfall", ""),
                    datum,
                    row.get("anzahl", ""),
                    row.get("depot_id", ""),
                    row.get("praeparat_id", ""),
                    row.get("empfaenger", "") or "",
                    has_pdf,
                    row.get("datei_name", "") or "",
                ]
            )
        return _csv_response("bewegungen_verlauf.csv", headers, data_rows)

    @app.get("/dashboard/overview")
    def dashboard_overview(
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session: SessionInfo = Depends(require_permission("movements_read")),
    ) -> dict:
        scoped_ids = _allowed_depot_ids(session, require_write=False)
        if session.role != "Admin" and not scoped_ids:
            return {"kpis": {"depots": 0, "praeparate": 0, "bewegungen": 0, "kritisch_verfallend": 0}, "recent_activity": [], "expiry_preview": []}
        safe_critical, safe_warning, safe_attention = _normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        payload = repository.get_dashboard_overview(limit_activity=8, limit_expiry=8, critical_days=safe_critical)
        if session.role != "Admin":
            scoped_set = set(scoped_ids)
            payload["recent_activity"] = [
                row for row in payload.get("recent_activity", []) if int(row.get("depot_id") or 0) in scoped_set
            ]
            payload["expiry_preview"] = [
                row for row in payload.get("expiry_preview", []) if int(row.get("depot_id") or 0) in scoped_set
            ]
            payload["kpis"]["depots"] = len(scoped_set)
        payload["expiry_preview"] = _enrich_verfall_rows(
            payload.get("expiry_preview", []),
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        payload["thresholds"] = {
            "kritisch_tage": safe_critical,
            "warnung_tage": safe_warning,
            "achtung_tage": safe_attention,
        }
        return payload

    @app.get("/verfall/overview")
    def verfall_overview(
        perspective: str = "depot",
        ids: str = "",
        q: str = "",
        category: str = "alle",
        limit: int = 100,
        offset: int = 0,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session: SessionInfo = Depends(require_permission("movements_read")),
    ) -> dict:
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = _parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        safe_critical, safe_warning, safe_attention = _normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        depot_ids = _scoped_requested_ids(
            session,
            selected_ids if safe_perspective == "depot" else [],
            require_write=False,
        ) if safe_perspective == "depot" else _allowed_depot_ids(session, require_write=False)
        if session.role != "Admin" and not depot_ids:
            return {"rows": [], "total": 0, "stats_page": {"kritisch": 0, "warnung": 0, "achtung": 0, "gesamt_menge": 0}}
        praeparat_ids = selected_ids if safe_perspective == "praeparat" and selected_ids else None
        rows = repository.list_verfall_items(
            depot_ids=depot_ids or None,
            praeparat_ids=praeparat_ids,
            search_text=q,
            category=category,
            limit=limit,
            offset=offset,
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        total = repository.count_verfall_items(
            depot_ids=depot_ids or None,
            praeparat_ids=praeparat_ids,
            search_text=q,
            category=category,
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        enriched_rows = _enrich_verfall_rows(rows, safe_critical, safe_warning, safe_attention)
        stats = {
            "kritisch": int(sum(1 for row in enriched_rows if row["kategorie"] == "kritisch")),
            "warnung": int(sum(1 for row in enriched_rows if row["kategorie"] == "warnung")),
            "achtung": int(sum(1 for row in enriched_rows if row["kategorie"] == "achtung")),
            "gesamt_menge": int(sum(int(row.get("anzahl") or 0) for row in enriched_rows)),
        }
        return {
            "rows": enriched_rows,
            "total": total,
            "stats_page": stats,
            "thresholds": {
                "kritisch_tage": safe_critical,
                "warnung_tage": safe_warning,
                "achtung_tage": safe_attention,
            },
        }

    @app.get("/verfall/overview/export.csv")
    def export_verfall_overview_csv(
        perspective: str = "depot",
        ids: str = "",
        q: str = "",
        category: str = "alle",
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session: SessionInfo = Depends(require_permission("movements_read")),
    ) -> StreamingResponse:
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = _parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        safe_critical, safe_warning, safe_attention = _normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        depot_ids = _scoped_requested_ids(
            session,
            selected_ids if safe_perspective == "depot" else [],
            require_write=False,
        ) if safe_perspective == "depot" else _allowed_depot_ids(session, require_write=False)
        if session.role != "Admin" and not depot_ids:
            return _csv_response("verfall_manager.csv", ["ID"], [])
        praeparat_ids = selected_ids if safe_perspective == "praeparat" and selected_ids else None
        rows = repository.list_verfall_items(
            depot_ids=depot_ids or None,
            praeparat_ids=praeparat_ids,
            search_text=q,
            category=category,
            limit=5000,
            offset=0,
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        enriched_rows = _enrich_verfall_rows(rows, safe_critical, safe_warning, safe_attention)
        csv_rows = [
            [
                row.get("id"),
                row.get("depot"),
                row.get("praeparat"),
                row.get("charge"),
                row.get("verfall"),
                row.get("tage_bis_verfall"),
                row.get("kategorie"),
                row.get("anzahl"),
            ]
            for row in enriched_rows
        ]
        return _csv_response(
            filename="verfall_manager.csv",
            headers=["ID", "Depot", "Praeparat", "Charge", "Verfall", "TageBisVerfall", "Kategorie", "Anzahl"],
            rows=csv_rows,
        )

    @app.get("/notifications/verfall")
    def notifications_verfall(
        since: str = "",
        limit: int = 25,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session: SessionInfo = Depends(require_permission("movements_read")),
    ) -> dict:
        allowed_ids = set(_allowed_depot_ids(session, require_write=False))
        if session.role != "Admin" and not allowed_ids:
            return {"since": (since or "").strip() or None, "next_since": datetime.now(UTC).isoformat(), "rows": [], "counts": {"kritisch": 0, "warnung": 0, "achtung": 0, "gesamt": 0}}
        safe_critical, safe_warning, safe_attention = _normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        now_iso = datetime.now(UTC).isoformat()
        rows = repository.list_new_critical_expiry_events(
            since_iso=(since or "").strip() or None,
            limit=limit,
            critical_days=safe_critical,
        )
        if session.role != "Admin":
            rows = [row for row in rows if int(row.get("depot_id") or 0) in allowed_ids]
        enriched_rows = _enrich_verfall_rows(rows, safe_critical, safe_warning, safe_attention)
        return {
            "since": (since or "").strip() or None,
            "next_since": now_iso,
            "rows": enriched_rows,
            "counts": {
                "kritisch": int(sum(1 for row in enriched_rows if row["kategorie"] == "kritisch")),
                "warnung": int(sum(1 for row in enriched_rows if row["kategorie"] == "warnung")),
                "achtung": int(sum(1 for row in enriched_rows if row["kategorie"] == "achtung")),
                "gesamt": len(enriched_rows),
            },
        }

    @app.post("/bewegungen", status_code=status.HTTP_201_CREATED)
    def create_bewegung(
        payload: BewegungCreateRequest,
        session: SessionInfo = Depends(require_permission("movements_write")),
    ) -> dict[str, int | str]:
        _ensure_depot_access(session, depot_id=payload.depot_id, require_write=True)
        try:
            new_id = repository.insert_bewegung(
                depot_id=payload.depot_id,
                praeparat_id=payload.praeparat_id,
                typ=payload.typ,
                charge=payload.charge,
                verfall=payload.verfall.isoformat(),
                datum=payload.datum.isoformat(),
                anzahl=payload.anzahl,
                empfaenger=payload.empfaenger,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="bewegung",
            resource_id=new_id,
            details={"typ": payload.typ, "depot_id": payload.depot_id, "praeparat_id": payload.praeparat_id},
        )
        return {"id": new_id, "status": "created"}

    @app.post("/bewegungen/{bewegung_id}/attachment", status_code=status.HTTP_201_CREATED)
    def upload_bewegung_attachment(
        bewegung_id: int,
        file: UploadFile = File(...),
        session: SessionInfo = Depends(require_permission("movements_write")),
    ) -> dict[str, int | str]:
        bewegung = repository.get_bewegung(bewegung_id)
        if bewegung is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bewegung nicht gefunden.")
        _ensure_depot_access(session, depot_id=int(bewegung.get("depot_id") or 0), require_write=True)
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        content_type = (file.content_type or "").lower()
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nur PDF-Dateien sind erlaubt.")
        if content_type and content_type not in PDF_MIME_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nur PDF-Dateien sind erlaubt.")
        depot_name = repository.get_depot_name(int(bewegung["depot_id"]))
        target_path = _build_attachment_target_path(
            app.state.attachments_dir,
            bewegung_id=bewegung_id,
            depot_name=depot_name,
            original_name=filename,
        )
        try:
            size = _persist_pdf_upload(file, target_path)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Datei konnte nicht gespeichert werden.") from exc
        stored_name = Path(filename).name
        uploaded_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        repository.set_bewegung_attachment(
            bewegung_id=bewegung_id,
            datei_pfad=str(target_path),
            datei_name=stored_name,
            datei_groesse=size,
            uploaded_at=uploaded_at,
        )
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="bewegung",
            resource_id=bewegung_id,
            details={"attachment": stored_name, "size": size},
        )
        return {"id": bewegung_id, "status": "attachment_saved"}

    @app.get("/bewegungen/{bewegung_id}/attachment")
    def get_bewegung_attachment(
        bewegung_id: int,
        download: bool = False,
        session: SessionInfo = Depends(require_permission("movements_read")),
    ) -> FileResponse:
        bewegung = repository.get_bewegung(bewegung_id)
        if bewegung is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bewegung nicht gefunden.")
        _ensure_depot_access(session, depot_id=int(bewegung.get("depot_id") or 0), require_write=False)
        datei_pfad = (bewegung.get("datei_pfad") or "").strip()
        if not datei_pfad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein PDF-Anhang vorhanden.")
        path = Path(datei_pfad)
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF-Datei nicht gefunden.")
        filename = (bewegung.get("datei_name") or path.name).strip() or path.name
        if download:
            return FileResponse(path=path, media_type="application/pdf", filename=filename)
        return FileResponse(path=path, media_type="application/pdf")

    @app.get("/imports/bewegungen/template")
    def download_bewegungen_template(
        session: SessionInfo = Depends(require_permission("import_use")),
    ) -> StreamingResponse:
        _ = session
        content = _build_import_template(repository)
        return StreamingResponse(
            BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="bewegungen_vorlage.xlsx"'},
        )

    @app.post("/imports/bewegungen/preview")
    def preview_import_bewegungen(
        file: UploadFile = File(...),
        session: SessionInfo = Depends(require_permission("import_use")),
    ) -> dict:
        _ = session
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        try:
            raw_df, row_offset = _load_import_dataframe(file)
            mapped_df = _map_import_columns(raw_df)
            parsed_rows, preview_rows, errors = _analyze_import_dataframe(repository, mapped_df, row_offset)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Datei konnte nicht gelesen werden: {exc}") from exc
        return {
            "filename": filename,
            "total_rows": int(len(mapped_df.dropna(how="all"))),
            "valid_rows": len(parsed_rows),
            "error_count": len(errors),
            "error_summary": _summarize_import_errors(errors),
            "preview_rows": preview_rows,
            "errors": errors[:100],
        }

    @app.post("/imports/bewegungen/execute")
    def execute_import_bewegungen(
        file: UploadFile = File(...),
        dry_run: bool = Form(False),
        session: SessionInfo = Depends(require_permission("import_use")),
    ) -> dict:
        _ = session
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        try:
            raw_df, row_offset = _load_import_dataframe(file)
            mapped_df = _map_import_columns(raw_df)
            parsed_rows, _preview_rows, errors = _analyze_import_dataframe(repository, mapped_df, row_offset)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Datei konnte nicht gelesen werden: {exc}") from exc

        import_fingerprint = _build_import_execution_fingerprint(filename, parsed_rows)
        if not dry_run:
            existing_batch = repository.get_import_batch_result(import_fingerprint)
            if existing_batch is not None:
                deduplicated_result = dict(existing_batch)
                deduplicated_result["filename"] = filename
                deduplicated_result["deduplicated"] = True
                deduplicated_result["import_fingerprint"] = import_fingerprint
                deduplicated_result["dry_run"] = False
                repository.log_audit(
                    username=session.username,
                    action="create",
                    resource_type="bewegung_import",
                    details={
                        "filename": filename,
                        "imported": deduplicated_result.get("imported"),
                        "errors": deduplicated_result.get("error_count"),
                        "import_fingerprint": import_fingerprint,
                        "deduplicated": True,
                        "dry_run": False,
                    },
                )
                return deduplicated_result

        allowed_write_ids = set(_allowed_depot_ids(session, require_write=True))
        if dry_run:
            would_imported = len(parsed_rows)
            if session.role != "Admin":
                would_imported = sum(1 for row in parsed_rows if int(row.get("depot_id") or 0) in allowed_write_ids)
            dry_result = {
                "filename": filename,
                "imported": 0,
                "would_imported": would_imported,
                "errors": errors[:200],
                "error_count": len(errors),
                "error_summary": _summarize_import_errors(errors),
                "deduplicated": False,
                "import_fingerprint": import_fingerprint,
                "dry_run": True,
            }
            repository.log_audit(
                username=session.username,
                action="create",
                resource_type="bewegung_import",
                details={
                    "filename": filename,
                    "would_imported": len(parsed_rows),
                    "errors": len(errors),
                    "import_fingerprint": import_fingerprint,
                    "deduplicated": False,
                    "dry_run": True,
                },
            )
            return dry_result

        imported = 0
        for row in parsed_rows:
            if session.role != "Admin" and int(row.get("depot_id") or 0) not in allowed_write_ids:
                errors.append(f"Zeile {row['display_row']}: Keine Schreibberechtigung auf Depot.")
                continue
            try:
                repository.insert_bewegung(
                    depot_id=row["depot_id"],
                    praeparat_id=row["praeparat_id"],
                    typ=row["typ"],
                    charge=row["charge"],
                    verfall=row["verfall"],
                    datum=row["datum"],
                    anzahl=row["anzahl"],
                    empfaenger=row["empfaenger"],
                )
                imported += 1
            except ValueError as exc:
                errors.append(f"Zeile {row['display_row']}: {exc}")

        result_payload = {
            "filename": filename,
            "imported": imported,
            "errors": errors[:200],
            "error_count": len(errors),
            "error_summary": _summarize_import_errors(errors),
            "deduplicated": False,
            "import_fingerprint": import_fingerprint,
            "dry_run": False,
        }
        repository.save_import_batch_result(
            batch_id=import_fingerprint,
            username=session.username,
            result=result_payload,
        )
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="bewegung_import",
            details={
                "filename": filename,
                "imported": imported,
                "errors": len(errors),
                "import_fingerprint": import_fingerprint,
                "deduplicated": False,
                "dry_run": False,
            },
        )
        return result_payload

    @app.get("/reports/bewegungen")
    def report_bewegungen(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = _parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        if not selected_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mindestens eine ID ist erforderlich.")
        scoped_depot_ids = _scoped_requested_ids(
            session,
            selected_ids if safe_perspective == "depot" else [],
            require_write=False,
        ) if safe_perspective == "depot" else _allowed_depot_ids(session, require_write=False)
        if session.role != "Admin" and not scoped_depot_ids:
            return {"rows": [], "kpis": {"gesamt": 0, "zugang": 0, "abgang": 0}}
        safe_start_date, safe_end_date = _validated_report_date_range(start_date, end_date)
        rows = repository.get_bewegungen_analyse(
            depot_ids=scoped_depot_ids if safe_perspective == "depot" else (scoped_depot_ids or None),
            praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
            start_date=safe_start_date,
            end_date=safe_end_date,
        )
        total = int(sum(int(row["anzahl"]) for row in rows))
        zugang = int(sum(int(row["anzahl"]) for row in rows if row["typ"] == "Zugang"))
        abgang = int(sum(int(row["anzahl"]) for row in rows if row["typ"] in {"Abgang", "Vernichtung"}))
        return {
            "rows": rows,
            "kpis": {"gesamt": total, "zugang": zugang, "abgang": abgang},
        }

    @app.get("/reports/bewegungen/export.csv")
    def export_report_bewegungen_csv(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> StreamingResponse:
        report = report_bewegungen(perspective, ids, start_date, end_date, session)
        rows = [
            [row["monat"], row["depot"], row["praeparat"], row["typ"], row["anzahl"]]
            for row in report["rows"]
        ]
        return _csv_response(
            filename=_build_report_export_filename(
                "bewegungsanalyse",
                "csv",
                perspective=perspective,
                start_date=start_date,
                end_date=end_date,
            ),
            headers=["Monat", "Depot", "Praeparat", "Typ", "Anzahl"],
            rows=rows,
        )

    @app.get("/reports/bestand")
    def report_bestand(
        perspective: str = "depot",
        ids: str = "",
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = _parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        if not selected_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mindestens eine ID ist erforderlich.")
        scoped_depot_ids = _scoped_requested_ids(
            session,
            selected_ids if safe_perspective == "depot" else [],
            require_write=False,
        ) if safe_perspective == "depot" else _allowed_depot_ids(session, require_write=False)
        if session.role != "Admin" and not scoped_depot_ids:
            return {"rows": [], "kpis": {"bestandsquote": 0.0, "kritische_luecken": 0, "gesamtbestand": 0}}
        rows = repository.get_bestandsentwicklung(
            depot_ids=scoped_depot_ids if safe_perspective == "depot" else (scoped_depot_ids or None),
            praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
        )
        sum_soll = int(sum(int(row["sollbestand"]) for row in rows))
        sum_ist = int(sum(int(row["ist_bestand"]) for row in rows))
        luecken = int(sum(1 for row in rows if int(row["differenz"]) < 0))
        quote = (sum_ist / sum_soll * 100) if sum_soll > 0 else 0.0
        return {
            "rows": rows,
            "kpis": {
                "bestandsquote": round(quote, 2),
                "kritische_luecken": luecken,
                "gesamtbestand": sum_ist,
            },
        }

    @app.get("/reports/bestand/export.csv")
    def export_report_bestand_csv(
        perspective: str = "depot",
        ids: str = "",
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> StreamingResponse:
        report = report_bestand(perspective, ids, session)
        rows = [
            [row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]]
            for row in report["rows"]
        ]
        return _csv_response(
            filename=_build_report_export_filename("bestandsentwicklung", "csv", perspective=perspective),
            headers=["Depot", "Praeparat", "Soll", "Ist", "Differenz"],
            rows=rows,
        )

    @app.get("/reports/ranking")
    def report_ranking(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 10,
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = _parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        if not selected_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mindestens eine ID ist erforderlich.")
        scoped_depot_ids = _scoped_requested_ids(
            session,
            selected_ids if safe_perspective == "depot" else [],
            require_write=False,
        ) if safe_perspective == "depot" else _allowed_depot_ids(session, require_write=False)
        if session.role != "Admin" and not scoped_depot_ids:
            return {"rows": [], "label": "praeparat" if safe_perspective == "depot" else "depot", "kpis": {"gesamtvolumen": 0}}
        safe_start_date, safe_end_date = _validated_report_date_range(start_date, end_date)
        if safe_perspective == "depot":
            raw_rows = repository.get_praeparat_ranking(
                depot_ids=scoped_depot_ids,
                start_date=safe_start_date,
                end_date=safe_end_date,
                limit=limit,
            )
            label = "praeparat"
        else:
            raw_rows = repository.get_depot_ranking(
                praeparat_ids=selected_ids,
                start_date=safe_start_date,
                end_date=safe_end_date,
                limit=limit,
            )
            label = "depot"
        rows: list[dict[str, int | str]] = []
        for row in raw_rows:
            item = row if isinstance(row, dict) else {}
            name = str(item.get("name") or item.get("depot") or item.get("praeparat") or "")
            try:
                anzahl = int(item.get("anzahl") or 0)
            except (TypeError, ValueError):
                anzahl = 0
            rows.append({"name": name, "anzahl": anzahl})
        ranking_basis = "abgang_vernichtung"
        if not rows:
            # Fallback: wenn es nur Zugangsbewegungen gibt, dennoch ein Ranking liefern.
            fallback_rows = repository.get_bewegungen_analyse(
                depot_ids=scoped_depot_ids if safe_perspective == "depot" else None,
                praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
                start_date=safe_start_date,
                end_date=safe_end_date,
            )
            aggregate: dict[str, int] = {}
            for item in fallback_rows:
                key = str(item.get("praeparat") if safe_perspective == "depot" else item.get("depot") or "")
                if not key:
                    continue
                try:
                    amount = int(item.get("anzahl") or 0)
                except (TypeError, ValueError):
                    amount = 0
                aggregate[key] = aggregate.get(key, 0) + amount
            rows = [
                {"name": key, "anzahl": value}
                for key, value in sorted(aggregate.items(), key=lambda kv: kv[1], reverse=True)[: max(1, min(int(limit), 50))]
            ]
            ranking_basis = "alle_bewegungen"
        total = int(sum(int(row.get("anzahl") or 0) for row in rows))
        return {"rows": rows, "label": label, "kpis": {"gesamtvolumen": total, "ranking_basis": ranking_basis}}

    @app.get("/reports/ranking/export.csv")
    def export_report_ranking_csv(
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 10,
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> StreamingResponse:
        report = report_ranking(perspective, ids, start_date, end_date, limit, session)
        rows = [
            [str(row.get("name") or ""), int(row.get("anzahl") or 0)]
            for row in report["rows"]
            if isinstance(row, dict)
        ]
        label_header = "Praeparat" if report["label"] == "praeparat" else "Depot"
        return _csv_response(
            filename=_build_report_export_filename(
                "ranking",
                "csv",
                perspective=perspective,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            ),
            headers=[label_header, "Anzahl"],
            rows=rows,
        )

    @app.get("/reports/matrix")
    def report_matrix(
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> dict:
        scoped_depot_ids = set(_allowed_depot_ids(session, require_write=False))
        if session.role != "Admin" and not scoped_depot_ids:
            return {"rows": []}
        allowed_depot_names = set()
        if session.role != "Admin":
            allowed_rows = repository.list_depots(limit=5000, offset=0, allowed_ids=list(scoped_depot_ids))
            allowed_depot_names = {str(row.get("name") or "") for row in allowed_rows}
        rows = repository.get_matrix_data()
        enriched = []
        for row in rows:
            if session.role != "Admin" and str(row.get("depot") or "") not in allowed_depot_names:
                continue
            diff = int(row["ist_bestand"]) - int(row["sollbestand"])
            item = dict(row)
            item["differenz"] = diff
            enriched.append(item)
        return {"rows": enriched}

    @app.get("/reports/matrix/export.csv")
    def export_report_matrix_csv(
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> StreamingResponse:
        report = report_matrix(session)
        rows = [
            [row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]]
            for row in report["rows"]
        ]
        return _csv_response(
            filename=_build_report_export_filename("matrix_bestand", "csv"),
            headers=["Depot", "Praeparat", "Soll", "Ist", "Differenz"],
            rows=rows,
        )

    @app.get("/reports/verfall")
    def report_verfall(
        perspective: str = "depot",
        ids: str = "",
        horizon_months: int = 24,
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> dict:
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = _parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        if not selected_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mindestens eine ID ist erforderlich.")
        rows = repository.get_verfall_prognose(
            depot_ids=selected_ids if safe_perspective == "depot" else None,
            praeparat_ids=selected_ids if safe_perspective == "praeparat" else None,
            horizon_months=horizon_months,
        )
        current_month = date.today().strftime("%Y-%m")
        horizon_end = _add_months(date.today().replace(day=1), max(1, min(int(horizon_months), 60))).strftime("%Y-%m")
        filtered_rows = [
            row
            for row in rows
            if row["verfall_monat"] and row["verfall_monat"] <= horizon_end
        ]
        bereits_verfallen = int(sum(int(row["anzahl"]) for row in filtered_rows if row["verfall_monat"] < current_month))
        return {
            "rows": filtered_rows,
            "kpis": {
                "bereits_verfallen": bereits_verfallen,
                "gesamt_vorschau": int(sum(int(row["anzahl"]) for row in filtered_rows)),
            },
        }

    @app.get("/reports/verfall/export.csv")
    def export_report_verfall_csv(
        perspective: str = "depot",
        ids: str = "",
        horizon_months: int = 24,
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> StreamingResponse:
        report = report_verfall(perspective, ids, horizon_months, session)
        rows = [[row["verfall_monat"], row["anzahl"]] for row in report["rows"]]
        return _csv_response(
            filename=_build_report_export_filename(
                "verfall_prognose",
                "csv",
                perspective=perspective,
                horizon_months=horizon_months,
            ),
            headers=["Verfall_Monat", "Anzahl"],
            rows=rows,
        )

    @app.get("/reports/{report_type}/export.pdf")
    def export_report_pdf(
        report_type: str,
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        horizon_months: int = 24,
        limit: int = 10,
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> StreamingResponse:
        safe_type = (report_type or "").strip().lower()
        if safe_type == "bewegungen":
            report = report_bewegungen(perspective, ids, start_date, end_date, session)
            headers = ["Monat", "Depot", "Praeparat", "Typ", "Anzahl"]
            rows = [[row["monat"], row["depot"], row["praeparat"], row["typ"], row["anzahl"]] for row in report["rows"]]
            return _pdf_response(
                _build_report_export_filename(
                    "bewegungsanalyse",
                    "pdf",
                    perspective=perspective,
                    start_date=start_date,
                    end_date=end_date,
                ),
                "Bewegungsanalyse",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "bestand":
            report = report_bestand(perspective, ids, session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return _pdf_response(
                _build_report_export_filename("bestandsentwicklung", "pdf", perspective=perspective),
                "Bestandsentwicklung",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "ranking":
            report = report_ranking(perspective, ids, start_date, end_date, limit, session)
            label_header = "Praeparat" if report["label"] == "praeparat" else "Depot"
            headers = [label_header, "Anzahl"]
            rows = [[row["name"], row["anzahl"]] for row in report["rows"]]
            return _pdf_response(
                _build_report_export_filename(
                    "ranking",
                    "pdf",
                    perspective=perspective,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                ),
                "Ranking",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "matrix":
            report = report_matrix(session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return _pdf_response(
                _build_report_export_filename("matrix_bestand", "pdf"),
                "Matrix Bestand",
                headers,
                rows,
                {},
            )
        if safe_type == "verfall":
            report = report_verfall(perspective, ids, horizon_months, session)
            headers = ["Verfall_Monat", "Anzahl"]
            rows = [[row["verfall_monat"], row["anzahl"]] for row in report["rows"]]
            return _pdf_response(
                _build_report_export_filename(
                    "verfall_prognose",
                    "pdf",
                    perspective=perspective,
                    horizon_months=horizon_months,
                ),
                "Verfall Prognose",
                headers,
                rows,
                report["kpis"],
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unbekannter Report-Typ.")

    @app.get("/reports/{report_type}/export.pptx")
    def export_report_pptx(
        report_type: str,
        perspective: str = "depot",
        ids: str = "",
        start_date: str = "",
        end_date: str = "",
        horizon_months: int = 24,
        limit: int = 10,
        session: SessionInfo = Depends(require_permission("reports_view")),
    ) -> StreamingResponse:
        safe_type = (report_type or "").strip().lower()
        if safe_type == "bewegungen":
            report = report_bewegungen(perspective, ids, start_date, end_date, session)
            headers = ["Monat", "Depot", "Praeparat", "Typ", "Anzahl"]
            rows = [[row["monat"], row["depot"], row["praeparat"], row["typ"], row["anzahl"]] for row in report["rows"]]
            return _pptx_response(
                _build_report_export_filename(
                    "bewegungsanalyse",
                    "pptx",
                    perspective=perspective,
                    start_date=start_date,
                    end_date=end_date,
                ),
                "Bewegungsanalyse",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "bestand":
            report = report_bestand(perspective, ids, session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return _pptx_response(
                _build_report_export_filename("bestandsentwicklung", "pptx", perspective=perspective),
                "Bestandsentwicklung",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "ranking":
            report = report_ranking(perspective, ids, start_date, end_date, limit, session)
            label_header = "Praeparat" if report["label"] == "praeparat" else "Depot"
            headers = [label_header, "Anzahl"]
            rows = [[row["name"], row["anzahl"]] for row in report["rows"]]
            return _pptx_response(
                _build_report_export_filename(
                    "ranking",
                    "pptx",
                    perspective=perspective,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                ),
                "Ranking",
                headers,
                rows,
                report["kpis"],
            )
        if safe_type == "matrix":
            report = report_matrix(session)
            headers = ["Depot", "Praeparat", "Soll", "Ist", "Differenz"]
            rows = [[row["depot"], row["praeparat"], row["sollbestand"], row["ist_bestand"], row["differenz"]] for row in report["rows"]]
            return _pptx_response(
                _build_report_export_filename("matrix_bestand", "pptx"),
                "Matrix Bestand",
                headers,
                rows,
                {},
            )
        if safe_type == "verfall":
            report = report_verfall(perspective, ids, horizon_months, session)
            headers = ["Verfall_Monat", "Anzahl"]
            rows = [[row["verfall_monat"], row["anzahl"]] for row in report["rows"]]
            return _pptx_response(
                _build_report_export_filename(
                    "verfall_prognose",
                    "pptx",
                    perspective=perspective,
                    horizon_months=horizon_months,
                ),
                "Verfall Prognose",
                headers,
                rows,
                report["kpis"],
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unbekannter Report-Typ.")

    def _parse_sync_cursor(raw_cursor: str | None) -> int:
        if raw_cursor is None:
            return 0
        text = str(raw_cursor).strip()
        if not text:
            return 0
        try:
            return max(0, int(text))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltiger Sync-Cursor.") from exc

    def _normalized_sync_entity(entity: str) -> str:
        safe = (entity or "").strip().lower()
        alias_map = {
            "depot": "depots",
            "depots": "depots",
            "praeparat": "praeparate",
            "praeparate": "praeparate",
            "kontakt": "kontakte",
            "kontakte": "kontakte",
            "bewegung": "bewegungen",
            "bewegungen": "bewegungen",
            "institution": "institutions",
            "institutions": "institutions",
            "depot_praeparat": "depot_praeparate",
            "depot_praeparate": "depot_praeparate",
        }
        return alias_map.get(safe, safe)

    def _expand_sync_entity_filters(raw_entities: list[str]) -> list[str]:
        expanded: set[str] = set()
        for raw in raw_entities or []:
            normalized = _normalized_sync_entity(raw)
            if not normalized:
                continue
            expanded.add(normalized)
            if normalized == "depots":
                expanded.add("depot")
            elif normalized == "praeparate":
                expanded.add("praeparat")
            elif normalized == "kontakte":
                expanded.add("kontakt")
            elif normalized == "bewegungen":
                expanded.add("bewegung")
            elif normalized == "institutions":
                expanded.add("institution")
            elif normalized == "depot_praeparate":
                expanded.add("depot_praeparat")
        return sorted(expanded)

    def _sync_permission_for_change(entity: str, operation: str) -> str:
        safe_entity = _normalized_sync_entity(entity)
        safe_operation = (operation or "").strip().lower()
        if safe_entity in {"depots", "praeparate", "institutions"}:
            return "masterdata_write"
        if safe_entity in {"kontakte", "depot_praeparate"}:
            return "settings_write"
        if safe_entity == "bewegungen":
            return "movements_write"
        if safe_operation in {"pull", "read", "list"}:
            return "movements_read"
        return "movements_write"

    def _serialize_sync_entity_payload(entity: str, entity_id: int | None) -> dict[str, Any]:
        safe_entity = _normalized_sync_entity(entity)
        safe_id = int(entity_id or 0)
        if safe_id <= 0:
            return {}
        if safe_entity == "institutions":
            return repository.get_institution(safe_id) or {}
        if safe_entity == "depots":
            return repository.get_depot(safe_id) or {}
        if safe_entity == "praeparate":
            return repository.get_praeparat(safe_id) or {}
        if safe_entity == "kontakte":
            return repository.get_kontakt(safe_id) or {}
        if safe_entity == "depot_praeparate":
            return repository.get_depot_assignment_by_id(safe_id) or {}
        if safe_entity == "bewegungen":
            row = repository.get_bewegung(safe_id) or {}
            if not row:
                return {}
            datum_value = row.get("eingang_datum") or row.get("ausgang_datum")
            depot = repository.get_depot(int(row.get("depot_id") or 0)) or {}
            praeparat = repository.get_praeparat(int(row.get("praeparat_id") or 0)) or {}
            payload = {
                "id": int(row.get("id") or 0),
                "depot_id": int(row.get("depot_id") or 0),
                "depot_name": str(depot.get("name") or ""),
                "praeparat_id": int(row.get("praeparat_id") or 0),
                "praeparat_name": str(praeparat.get("name") or ""),
                "typ": row.get("typ"),
                "charge": row.get("charge"),
                "verfall": row.get("verfall"),
                "datum": datum_value,
                "anzahl": int(row.get("anzahl") or 0),
                "empfaenger": row.get("empfaenger"),
            }
            return payload
        return {}

    def _build_sync_pull_change(change: dict[str, Any]) -> dict[str, Any] | None:
        safe_entity = _normalized_sync_entity(str(change.get("entity") or ""))
        safe_operation = str(change.get("operation") or "").strip().lower()
        if safe_entity not in {"institutions", "depots", "praeparate", "kontakte", "depot_praeparate", "bewegungen"}:
            return None
        if safe_operation not in {"create", "update", "delete"}:
            return None

        raw_entity_id = change.get("entity_id")
        entity_id: int | None = None
        try:
            if raw_entity_id is not None:
                entity_id = int(raw_entity_id)
        except (TypeError, ValueError):
            entity_id = None

        if safe_operation == "delete":
            payload = {"id": int(entity_id or 0)}
        else:
            payload = _serialize_sync_entity_payload(safe_entity, entity_id)
            if not payload:
                # Datensatz inzwischen entfernt -> als Delete-Tombstone ausliefern.
                payload = {"id": int(entity_id or 0)}
                safe_operation = "delete"

        return {
            "change_id": int(change.get("change_id") or 0),
            "changed_at": str(change.get("changed_at") or ""),
            "entity": safe_entity,
            "operation": safe_operation,
            "payload": payload,
        }

    def _is_sync_change_allowed_for_session(session: SessionInfo, built_change: dict[str, Any]) -> bool:
        if session.role == "Admin":
            return True
        entity = _normalized_sync_entity(str(built_change.get("entity") or ""))
        payload = dict(built_change.get("payload") or {})
        allowed_read_ids = set(_allowed_depot_ids(session, require_write=False))
        if entity == "depots":
            depot_id = int(payload.get("id") or 0)
            return depot_id > 0 and depot_id in allowed_read_ids
        if entity in {"kontakte", "bewegungen", "depot_praeparate"}:
            depot_id = int(payload.get("depot_id") or 0)
            return depot_id > 0 and depot_id in allowed_read_ids
        # institutions/praeparate currently treated as globally visible for read.
        return True

    def _apply_sync_change(change: SyncPushChangeItem, session: SessionInfo) -> dict[str, Any]:
        safe_entity = _normalized_sync_entity(change.entity)
        safe_operation = (change.operation or "").strip().lower()
        payload = dict(change.payload or {})
        client_change_id = (change.client_change_id or "").strip() or None

        if safe_entity == "depots":
            if safe_operation == "create":
                new_id = repository.create_depot(
                    name=str(payload.get("name") or ""),
                    adresse=payload.get("adresse"),
                    strasse=payload.get("strasse"),
                    hausnummer=payload.get("hausnummer"),
                    postleitzahl=payload.get("postleitzahl"),
                    stadt=payload.get("stadt"),
                    telefon=payload.get("telefon"),
                    email=payload.get("email"),
                    institution_id=payload.get("institution_id"),
                    latitude=payload.get("latitude"),
                    longitude=payload.get("longitude"),
                )
                repository.log_audit(
                    username=session.username,
                    action="create",
                    resource_type="depots",
                    resource_id=new_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "depots", "operation": "create", "server_id": new_id}
            if safe_operation == "update":
                depot_id = int(payload.get("id") or 0)
                changed = repository.update_depot(
                    depot_id=depot_id,
                    name=str(payload.get("name") or ""),
                    adresse=payload.get("adresse"),
                    strasse=payload.get("strasse"),
                    hausnummer=payload.get("hausnummer"),
                    postleitzahl=payload.get("postleitzahl"),
                    stadt=payload.get("stadt"),
                    telefon=payload.get("telefon"),
                    email=payload.get("email"),
                    institution_id=payload.get("institution_id"),
                    latitude=payload.get("latitude"),
                    longitude=payload.get("longitude"),
                )
                if not changed:
                    raise LookupError("Depot nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="update",
                    resource_type="depots",
                    resource_id=depot_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "depots", "operation": "update", "server_id": depot_id}
            if safe_operation == "delete":
                depot_id = int(payload.get("id") or 0)
                changed = repository.delete_depot(depot_id)
                if not changed:
                    raise LookupError("Depot nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="delete",
                    resource_type="depots",
                    resource_id=depot_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "depots", "operation": "delete", "server_id": depot_id}
            raise ValueError("Operation fuer depots nicht unterstuetzt.")

        if safe_entity == "institutions":
            if safe_operation == "create":
                new_id = repository.create_institution(
                    name=str(payload.get("name") or ""),
                    adresse=payload.get("adresse"),
                    strasse=payload.get("strasse"),
                    hausnummer=payload.get("hausnummer"),
                    postleitzahl=payload.get("postleitzahl"),
                    stadt=payload.get("stadt"),
                    latitude=payload.get("latitude"),
                    longitude=payload.get("longitude"),
                )
                repository.log_audit(
                    username=session.username,
                    action="create",
                    resource_type="institutions",
                    resource_id=new_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "institutions", "operation": "create", "server_id": new_id}
            if safe_operation == "update":
                institution_id = int(payload.get("id") or 0)
                changed = repository.update_institution(
                    institution_id=institution_id,
                    name=str(payload.get("name") or ""),
                    adresse=payload.get("adresse"),
                    strasse=payload.get("strasse"),
                    hausnummer=payload.get("hausnummer"),
                    postleitzahl=payload.get("postleitzahl"),
                    stadt=payload.get("stadt"),
                    latitude=payload.get("latitude"),
                    longitude=payload.get("longitude"),
                )
                if not changed:
                    raise LookupError("Institution nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="update",
                    resource_type="institutions",
                    resource_id=institution_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "institutions", "operation": "update", "server_id": institution_id}
            if safe_operation == "delete":
                institution_id = int(payload.get("id") or 0)
                changed = repository.delete_institution(institution_id)
                if not changed:
                    raise LookupError("Institution nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="delete",
                    resource_type="institutions",
                    resource_id=institution_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "institutions", "operation": "delete", "server_id": institution_id}
            raise ValueError("Operation fuer institutions nicht unterstuetzt.")

        if safe_entity == "praeparate":
            if safe_operation == "create":
                new_id = repository.create_praeparat(
                    name=str(payload.get("name") or ""),
                    wirkstoff=payload.get("wirkstoff"),
                    darreichungsform=payload.get("darreichungsform"),
                    staerke=payload.get("staerke"),
                    einheit=payload.get("einheit"),
                    pzn=payload.get("pzn"),
                    hersteller=payload.get("hersteller"),
                )
                repository.log_audit(
                    username=session.username,
                    action="create",
                    resource_type="praeparate",
                    resource_id=new_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "praeparate", "operation": "create", "server_id": new_id}
            if safe_operation == "update":
                praeparat_id = int(payload.get("id") or 0)
                changed = repository.update_praeparat(
                    praeparat_id=praeparat_id,
                    name=str(payload.get("name") or ""),
                    wirkstoff=payload.get("wirkstoff"),
                    darreichungsform=payload.get("darreichungsform"),
                    staerke=payload.get("staerke"),
                    einheit=payload.get("einheit"),
                    pzn=payload.get("pzn"),
                    hersteller=payload.get("hersteller"),
                )
                if not changed:
                    raise LookupError("Praeparat nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="update",
                    resource_type="praeparate",
                    resource_id=praeparat_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "praeparate", "operation": "update", "server_id": praeparat_id}
            if safe_operation == "delete":
                praeparat_id = int(payload.get("id") or 0)
                changed = repository.delete_praeparat(praeparat_id)
                if not changed:
                    raise LookupError("Praeparat nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="delete",
                    resource_type="praeparate",
                    resource_id=praeparat_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "praeparate", "operation": "delete", "server_id": praeparat_id}
            raise ValueError("Operation fuer praeparate nicht unterstuetzt.")

        if safe_entity == "kontakte":
            if safe_operation == "create":
                new_id = repository.create_kontakt(
                    depot_id=int(payload.get("depot_id") or 0),
                    name=str(payload.get("name") or ""),
                    rolle=payload.get("rolle"),
                    telefon=payload.get("telefon"),
                    email=payload.get("email"),
                )
                repository.log_audit(
                    username=session.username,
                    action="create",
                    resource_type="kontakte",
                    resource_id=new_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "kontakte", "operation": "create", "server_id": new_id}
            if safe_operation == "update":
                kontakt_id = int(payload.get("id") or 0)
                changed = repository.update_kontakt(
                    kontakt_id=kontakt_id,
                    name=str(payload.get("name") or ""),
                    rolle=payload.get("rolle"),
                    telefon=payload.get("telefon"),
                    email=payload.get("email"),
                )
                if not changed:
                    raise LookupError("Kontakt nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="update",
                    resource_type="kontakte",
                    resource_id=kontakt_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "kontakte", "operation": "update", "server_id": kontakt_id}
            if safe_operation == "delete":
                kontakt_id = int(payload.get("id") or 0)
                changed = repository.delete_kontakt(kontakt_id)
                if not changed:
                    raise LookupError("Kontakt nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="delete",
                    resource_type="kontakte",
                    resource_id=kontakt_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "kontakte", "operation": "delete", "server_id": kontakt_id}
            raise ValueError("Operation fuer kontakte nicht unterstuetzt.")

        if safe_entity == "depot_praeparate":
            depot_id = int(payload.get("depot_id") or 0)
            praeparat_id = int(payload.get("praeparat_id") or 0)
            if safe_operation in {"create", "update"}:
                assignment_id = repository.upsert_depot_assignment(
                    depot_id=depot_id,
                    praeparat_id=praeparat_id,
                    sollbestand=int(payload.get("sollbestand") or 0),
                )
                repository.log_audit(
                    username=session.username,
                    action="update" if safe_operation == "update" else "create",
                    resource_type="depot_praeparate",
                    resource_id=assignment_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "depot_praeparate", "operation": safe_operation, "server_id": assignment_id}
            if safe_operation == "delete":
                existing = repository.get_depot_assignment(depot_id=depot_id, praeparat_id=praeparat_id)
                assignment_id = int((existing or {}).get("id") or 0)
                deleted = repository.delete_depot_assignment(depot_id=depot_id, praeparat_id=praeparat_id)
                if not deleted:
                    raise LookupError("Depot-Praeparat-Zuordnung nicht gefunden.")
                repository.log_audit(
                    username=session.username,
                    action="delete",
                    resource_type="depot_praeparate",
                    resource_id=assignment_id,
                    details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
                )
                return {"entity": "depot_praeparate", "operation": "delete", "server_id": assignment_id}
            raise ValueError("Operation fuer depot_praeparate nicht unterstuetzt.")

        if safe_entity == "bewegungen":
            if safe_operation != "create":
                raise ValueError("Fuer bewegungen ist in v1 nur create unterstuetzt.")
            typ_raw = str(payload.get("typ") or "").strip()
            safe_typ = {
                "zugang": "Zugang",
                "abgang": "Abgang",
                "vernichtung": "Vernichtung",
            }.get(typ_raw.lower(), typ_raw)

            depot_id = int(payload.get("depot_id") or 0)
            praeparat_id = int(payload.get("praeparat_id") or 0)
            depot_name = str(payload.get("depot_name") or "").strip()
            praeparat_name = str(payload.get("praeparat_name") or "").strip()

            if depot_id > 0:
                depot_exists = repository.get_depot(depot_id)
                if not depot_exists:
                    depot_id = 0
            if praeparat_id > 0:
                prae_exists = repository.get_praeparat(praeparat_id)
                if not prae_exists:
                    praeparat_id = 0

            if depot_id <= 0 and depot_name:
                depot_matches = [
                    int(row.get("id") or 0)
                    for row in repository.list_depots(q=depot_name, limit=200, offset=0)
                    if str(row.get("name") or "").strip().lower() == depot_name.lower()
                ]
                unique_depot_ids = sorted({d for d in depot_matches if d > 0})
                if len(unique_depot_ids) == 1:
                    depot_id = unique_depot_ids[0]
                elif len(unique_depot_ids) > 1:
                    raise ValueError("Depot-Name ist nicht eindeutig; bitte depot_id verwenden.")

            if praeparat_id <= 0 and praeparat_name:
                prae_matches = [
                    int(row.get("id") or 0)
                    for row in repository.list_praeparate(q=praeparat_name, limit=200, offset=0)
                    if str(row.get("name") or "").strip().lower() == praeparat_name.lower()
                ]
                unique_prae_ids = sorted({p for p in prae_matches if p > 0})
                if len(unique_prae_ids) == 1:
                    praeparat_id = unique_prae_ids[0]
                elif len(unique_prae_ids) > 1:
                    raise ValueError("Praeparat-Name ist nicht eindeutig; bitte praeparat_id verwenden.")

            new_id = repository.insert_bewegung(
                depot_id=depot_id,
                praeparat_id=praeparat_id,
                typ=safe_typ,
                charge=str(payload.get("charge") or ""),
                verfall=str(payload.get("verfall") or ""),
                datum=str(payload.get("datum") or ""),
                anzahl=int(payload.get("anzahl") or 0),
                empfaenger=payload.get("empfaenger"),
            )
            repository.log_audit(
                username=session.username,
                action="create",
                resource_type="bewegungen",
                resource_id=new_id,
                details={"source": "sync_push", "batch": "v1", "client_change_id": client_change_id},
            )
            return {"entity": "bewegungen", "operation": "create", "server_id": new_id}

        raise ValueError(f"Unbekannte Sync-Entity: {safe_entity}")

    @app.get("/sync/status")
    def sync_status(session: SessionInfo = Depends(get_current_session)) -> dict[str, Any]:
        _ = session
        return {
            "server_time": datetime.now(UTC).isoformat(),
            "min_supported_client_version": "1.0.0",
            "features": {
                "entities": ["institutions", "depots", "praeparate", "kontakte", "depot_praeparate", "bewegungen"],
                "operations": ["create", "update", "delete"],
                "idempotent_push": True,
                "cursor_pull": True,
            },
        }

    @app.post("/sync/pull")
    def sync_pull(
        payload: SyncPullRequest,
        session: SessionInfo = Depends(get_current_session),
    ) -> dict[str, Any]:
        safe_cursor = _parse_sync_cursor(payload.cursor)
        filter_entities = _expand_sync_entity_filters(payload.entities)
        result = repository.list_sync_audit_changes(
            cursor=safe_cursor,
            entities=filter_entities,
            limit=payload.limit,
        )
        transformed_changes: list[dict[str, Any]] = []
        for item in result.get("changes") or []:
            built = _build_sync_pull_change(dict(item))
            if built is not None and _is_sync_change_allowed_for_session(session, built):
                transformed_changes.append(built)
        result["changes"] = transformed_changes
        result["server_time"] = datetime.now(UTC).isoformat()
        return result

    @app.post("/sync/push")
    def sync_push(
        payload: SyncPushRequest,
        session: SessionInfo = Depends(get_current_session),
    ) -> dict[str, Any]:
        existing = repository.get_sync_batch_result(payload.batch_id)
        if existing is not None:
            existing["deduplicated"] = True
            return existing

        user_permissions = _user_permissions(session.username, session.role)
        allowed_write_ids = set(_allowed_depot_ids(session, require_write=True))
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []

        for index, change in enumerate(payload.changes):
            required_permission = _sync_permission_for_change(change.entity, change.operation)
            if session.role != "Admin" and required_permission not in user_permissions:
                rejected.append(
                    {
                        "index": index,
                        "entity": change.entity,
                        "operation": change.operation,
                        "reason": f"Berechtigung fehlt ({required_permission}).",
                    }
                )
                continue
            if session.role != "Admin":
                safe_entity = _normalized_sync_entity(change.entity)
                payload_map = dict(change.payload or {})
                if safe_entity == "depots" and (change.operation or "").strip().lower() in {"update", "delete"}:
                    depot_id = int(payload_map.get("id") or 0)
                    if depot_id <= 0 or depot_id not in allowed_write_ids:
                        rejected.append(
                            {
                                "index": index,
                                "entity": change.entity,
                                "operation": change.operation,
                                "reason": "Depot-Berechtigung fehlt.",
                                "client_change_id": change.client_change_id,
                            }
                        )
                        continue
                if safe_entity in {"kontakte", "bewegungen", "depot_praeparate"}:
                    depot_id = int(payload_map.get("depot_id") or 0)
                    if depot_id <= 0 or depot_id not in allowed_write_ids:
                        rejected.append(
                            {
                                "index": index,
                                "entity": change.entity,
                                "operation": change.operation,
                                "reason": "Depot-Berechtigung fehlt.",
                                "client_change_id": change.client_change_id,
                            }
                        )
                        continue
            try:
                applied = _apply_sync_change(change, session)
                accepted.append(
                    {
                        "index": index,
                        "entity": applied.get("entity"),
                        "operation": applied.get("operation"),
                        "server_id": applied.get("server_id"),
                        "client_change_id": change.client_change_id,
                    }
                )
            except LookupError as exc:
                conflicts.append(
                    {
                        "index": index,
                        "entity": change.entity,
                        "operation": change.operation,
                        "reason": str(exc),
                        "client_change_id": change.client_change_id,
                    }
                )
            except ValueError as exc:
                rejected.append(
                    {
                        "index": index,
                        "entity": change.entity,
                        "operation": change.operation,
                        "reason": str(exc),
                        "client_change_id": change.client_change_id,
                    }
                )

        response = {
            "batch_id": payload.batch_id,
            "accepted": accepted,
            "rejected": rejected,
            "conflicts": conflicts,
            "server_cursor": str(repository.get_latest_audit_cursor()),
            "deduplicated": False,
        }
        repository.save_sync_batch_result(payload.batch_id, session.username, response)
        return response

    @app.get("/sync/ops/stats")
    def sync_ops_stats(
        session: SessionInfo = Depends(require_permission("audit_view")),
    ) -> dict[str, Any]:
        stats = repository.get_sync_ops_stats()
        stats["server_time"] = datetime.now(UTC).isoformat()
        stats["requested_by"] = session.username
        return stats

    @app.get("/audit-logs")
    def list_audit_logs(
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        action: str = "",
        resource_type: str = "",
        session: SessionInfo = Depends(require_permission("audit_view")),
    ) -> list[dict]:
        _ = session
        return repository.list_audit_logs(
            limit=limit,
            offset=offset,
            q=q,
            action=action,
            resource_type=resource_type,
        )

    return app


app = create_app()

