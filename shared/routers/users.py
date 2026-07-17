"""Shared Users-Router — CRUD + admin password ops.

Issues #60/#61/#65. Web-only depot-permission routes are optional via flag.
PUT uses the stricter web rules (self-protect + last-admin guard) for both backends.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status


def create_users_router(
    security,
    repository,
    require_permission,
    *,
    normalize_user_row,
    permissions_json_for_storage,
    allowed_user_roles,
    hash_password,
    user_create_model,
    user_update_model,
    user_password_reset_model,
    include_depot_permissions: bool = False,
    user_depot_permission_update_model=None,
    is_multi_institution=None,
) -> APIRouter:
    UserCreateRequest = user_create_model
    UserUpdateRequest = user_update_model
    UserPasswordResetRequest = user_password_reset_model
    UserDepotPermissionUpdateRequest = user_depot_permission_update_model
    router = APIRouter(prefix="/users", tags=["users"])

    @router.get("/")
    def list_users(
        session=Depends(require_permission("users_manage")),
    ) -> list[dict]:
        _ = session
        return [normalize_user_row(row) for row in security.list_users()]

    @router.get("/{user_id}/activity")
    def list_user_activity(
        user_id: int,
        limit: int = 100,
        session=Depends(require_permission("users_manage")),
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

    @router.post("/", status_code=status.HTTP_201_CREATED)
    def create_user(
        payload: UserCreateRequest,
        session=Depends(require_permission("users_manage")),
    ) -> dict:
        _ = session
        safe_username = payload.username.strip()
        if not safe_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benutzername darf nicht leer sein.")
        safe_role = payload.role.strip()
        if safe_role not in allowed_user_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Rolle.")
        exists = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (safe_username,),
        ).fetchone()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Benutzername existiert bereits.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        password_hash = hash_password(payload.password)
        permissions_json = permissions_json_for_storage(safe_role, payload.permissions)
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
        return normalize_user_row(row)

    @router.put("/{user_id}")
    def update_user(
        user_id: int,
        payload: UserUpdateRequest,
        session=Depends(require_permission("users_manage")),
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sie können sich nicht selbst deaktivieren.",
                )
            if payload.role is not None and requested_role != current_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sie können Ihre eigene Rolle nicht aendern.",
                )

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
            if safe_role not in allowed_user_roles:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Rolle.")
            updates.append("role = ?")
            params.append(safe_role)
        if payload.email is not None:
            updates.append("email = ?")
            params.append((payload.email or "").strip() or None)
        if payload.permissions is not None:
            effective_role = payload.role.strip() if payload.role else str(row[2])
            updates.append("permissions = ?")
            params.append(permissions_json_for_storage(effective_role, payload.permissions))
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
        return normalize_user_row(refreshed)

    @router.delete("/{user_id}")
    def delete_user(
        user_id: int,
        session=Depends(require_permission("users_manage")),
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Letzter aktiver Admin darf nicht gelöscht werden.",
                )
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

    @router.post("/{user_id}/reset-password")
    def reset_user_password(
        user_id: int,
        payload: UserPasswordResetRequest,
        session=Depends(require_permission("users_manage")),
    ) -> dict[str, int | str]:
        _ = session
        row = security.cur.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        new_hash = hash_password(payload.new_password)
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

    @router.post("/{user_id}/unlock")
    def unlock_user(
        user_id: int,
        session=Depends(require_permission("users_manage")),
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

    if include_depot_permissions:
        if user_depot_permission_update_model is None or is_multi_institution is None:
            raise ValueError("depot permission routes require model + is_multi_institution")

        @router.get("/{username}/depot-permissions")
        def get_user_depot_permissions(
            username: str,
            session=Depends(require_permission("users_manage")),
        ) -> list[dict]:
            _ = session
            if not is_multi_institution():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
            if not hasattr(repository, "list_user_depot_permissions"):
                return []
            return repository.list_user_depot_permissions(username)

        @router.put("/depot-permissions")
        def update_user_depot_permissions(
            payload: UserDepotPermissionUpdateRequest,
            session=Depends(require_permission("users_manage")),
        ) -> dict[str, str | int]:
            _ = session
            if not is_multi_institution():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
            if not hasattr(repository, "set_user_depot_permission"):
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Depot-Rechte nicht verfgbar.",
                )
            for item in payload.permissions:
                repository.set_user_depot_permission(
                    username=payload.username,
                    depot_id=item.depot_id,
                    can_read=item.can_read,
                    can_write=item.can_write,
                )
            return {"status": "updated", "count": len(payload.permissions)}

    return router
