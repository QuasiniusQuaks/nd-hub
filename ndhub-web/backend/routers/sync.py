"""Web sync pull/push/status/ops routes + helpers (Issue #60)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

try:
    from datetime import UTC
except ImportError:  # pragma: no cover
    from datetime import timezone
    UTC = timezone.utc


def create_sync_router(repository, require_permission, get_current_session, SyncPushRequest, SyncPushChangeItem, SyncPullRequest, _allowed_depot_ids, _user_permissions) -> APIRouter:
    router = APIRouter()

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

    def _is_sync_change_allowed_for_session(session, built_change: dict[str, Any]) -> bool:
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

    def _apply_sync_change(change: SyncPushChangeItem, session) -> dict[str, Any]:
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

    @router.get("/sync/status")
    def sync_status(session = Depends(get_current_session)) -> dict[str, Any]:
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

    @router.post("/sync/pull")
    def sync_pull(
        payload: SyncPullRequest,
        session = Depends(get_current_session),
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

    @router.post("/sync/push")
    def sync_push(
        payload: SyncPushRequest,
        session = Depends(get_current_session),
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

    @router.get("/sync/ops/stats")
    def sync_ops_stats(
        session = Depends(require_permission("audit_view")),
    ) -> dict[str, Any]:
        stats = repository.get_sync_ops_stats()
        stats["server_time"] = datetime.now(UTC).isoformat()
        stats["requested_by"] = session.username
        return stats


    return router
