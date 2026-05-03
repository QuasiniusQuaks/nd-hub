"""Simple token authentication for MVP backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
import sqlite3
from pathlib import Path
from typing import Any
import hashlib

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass
class SessionInfo:
    username: str
    role: str | None
    expires_at: datetime


class TokenStore:
    """Token storage with optional SQLite persistence."""

    def __init__(self, ttl_hours: int = 12, storage_path: str | None = None):
        self.ttl = timedelta(hours=ttl_hours)
        self._tokens: dict[str, SessionInfo] = {}
        self._storage_path = str(storage_path or "").strip()
        self._db: sqlite3.Connection | None = None
        if self._storage_path:
            self._init_storage()
            self._load_persisted_tokens()

    def _init_storage(self) -> None:
        storage_file = Path(self._storage_path)
        storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self._storage_path, check_same_thread=False)
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT,
                token_type TEXT NOT NULL DEFAULT 'session',
                token_label TEXT,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            )
            """
        )
        columns = {
            str(row[1] or "")
            for row in self._db.execute("PRAGMA table_info(auth_tokens)").fetchall()
        }
        if "token_label" not in columns:
            self._db.execute("ALTER TABLE auth_tokens ADD COLUMN token_label TEXT")
        self._db.commit()

    @staticmethod
    def _parse_iso_utc(value: Any) -> datetime | None:
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
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _load_persisted_tokens(self) -> None:
        if self._db is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute("DELETE FROM auth_tokens WHERE revoked_at IS NULL AND expires_at <= ?", (now,))
        self._db.commit()
        rows = self._db.execute(
            """
            SELECT token, username, role, expires_at
            FROM auth_tokens
            WHERE revoked_at IS NULL
            """
        ).fetchall()
        for token, username, role, expires_at_raw in rows:
            expires_at = self._parse_iso_utc(expires_at_raw)
            if expires_at is None:
                continue
            if expires_at <= datetime.now(timezone.utc):
                continue
            self._tokens[str(token)] = SessionInfo(
                username=str(username or ""),
                role=str(role) if role is not None else None,
                expires_at=expires_at,
            )

    @staticmethod
    def _fingerprint(token: str) -> str:
        return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()[:24]

    def issue(
        self,
        username: str,
        role: str | None,
        ttl_hours: int | None = None,
        token_type: str = "session",
        token_label: str | None = None,
    ) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        ttl = self.ttl
        if ttl_hours is not None:
            ttl = timedelta(hours=max(1, min(int(ttl_hours), 24 * 365 * 20)))
        expires_at = now + ttl
        session_info = SessionInfo(
            username=username,
            role=role,
            expires_at=expires_at,
        )
        self._tokens[token] = session_info
        if self._db is not None:
            self._db.execute(
                """
                INSERT OR REPLACE INTO auth_tokens (token, username, role, token_type, token_label, issued_at, expires_at, revoked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    token,
                    username,
                    role,
                    str(token_type or "session"),
                    str(token_label or "").strip() or None,
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            self._db.commit()
        return token

    def get(self, token: str) -> SessionInfo | None:
        token = str(token or "")
        info = self._tokens.get(token)
        if info is None and self._db is not None:
            row = self._db.execute(
                """
                SELECT username, role, expires_at
                FROM auth_tokens
                WHERE token = ? AND revoked_at IS NULL
                LIMIT 1
                """,
                (token,),
            ).fetchone()
            if row is not None:
                expires_at = self._parse_iso_utc(row[2])
                if expires_at is not None:
                    info = SessionInfo(
                        username=str(row[0] or ""),
                        role=str(row[1]) if row[1] is not None else None,
                        expires_at=expires_at,
                    )
                    self._tokens[token] = info
        if info is None:
            return None
        if info.expires_at <= datetime.now(timezone.utc):
            self._tokens.pop(token, None)
            if self._db is not None:
                self._db.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
                self._db.commit()
            return None
        return info

    def revoke(self, token: str) -> bool:
        token = str(token or "")
        removed = self._tokens.pop(token, None) is not None
        if self._db is not None:
            revoked_at = datetime.now(timezone.utc).isoformat()
            cur = self._db.execute(
                "UPDATE auth_tokens SET revoked_at = ? WHERE token = ? AND revoked_at IS NULL",
                (revoked_at, token),
            )
            self._db.commit()
            if cur.rowcount > 0:
                removed = True
        return removed

    def list_tokens(self, token_type: str | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if self._db is None:
            now = datetime.now(timezone.utc)
            for token, info in self._tokens.items():
                rows.append(
                    {
                        "token": token,
                        "token_label": None,
                        "username": info.username,
                        "role": info.role,
                        "token_type": "session",
                        "issued_at": now.isoformat(),
                        "expires_at": info.expires_at.isoformat(),
                        "revoked_at": None,
                    }
                )
            return rows
        params: list[Any] = []
        query = """
            SELECT token, username, role, token_type, token_label, issued_at, expires_at, revoked_at
            FROM auth_tokens
        """
        if token_type:
            query += " WHERE token_type = ?"
            params.append(str(token_type))
        query += " ORDER BY issued_at DESC"
        fetched = self._db.execute(query, tuple(params)).fetchall()
        for row in fetched:
            rows.append(
                {
                    "token": str(row[0] or ""),
                    "fingerprint": self._fingerprint(str(row[0] or "")),
                    "username": str(row[1] or ""),
                    "role": str(row[2]) if row[2] is not None else None,
                    "token_type": str(row[3] or "session"),
                    "token_label": str(row[4] or "").strip() or None,
                    "issued_at": str(row[5] or ""),
                    "expires_at": str(row[6] or ""),
                    "revoked_at": str(row[7] or "") if row[7] is not None else None,
                }
            )
        return rows

    def revoke_by_fingerprint(self, fingerprint: str, token_type: str | None = None) -> bool:
        wanted = str(fingerprint or "").strip().lower()
        if not wanted:
            return False
        for entry in self.list_tokens(token_type=token_type):
            token = str(entry.get("token") or "")
            token_fp = str(entry.get("fingerprint") or "").lower()
            if token and token_fp == wanted:
                return self.revoke(token)
        return False

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SessionInfo:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    token_store: TokenStore = request.app.state.token_store
    info = token_store.get(credentials.credentials)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return info


def require_admin_session(
    session: SessionInfo = Depends(get_current_session),
) -> SessionInfo:
    if session.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin-Rechte erforderlich.",
        )
    return session

