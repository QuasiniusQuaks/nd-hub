"""Domain helpers for ND-Hub web backend (Issue #96)."""

from __future__ import annotations

import io
import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import HTTPException, UploadFile, status

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


from backend.config import resolve_mariadb_settings
from backend.helper_common import (
    _normalize_json_value,
    _quote_sql_identifier,
    _safe_backup_label,
)


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


