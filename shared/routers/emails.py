"""Shared Emails router (Issues #60/#61).

Web enables kontakt filtering, SMTP send-now, delivery status endpoints.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status


def create_emails_router(
    repository,
    require_permission,
    *,
    email_recipient_preview_model,
    email_draft_create_model,
    enable_web_features: bool = False,
    email_delivery_status_update_model=None,
    get_email_delivery_settings=None,
    email_delivery_missing_config=None,
    send_email_via_smtp=None,
) -> APIRouter:
    EmailRecipientPreviewRequest = email_recipient_preview_model
    EmailDraftCreateRequest = email_draft_create_model
    EmailDeliveryStatusUpdateRequest = email_delivery_status_update_model
    router = APIRouter(prefix="/emails", tags=["emails"])

    @router.post("/recipients-preview")
    def preview_email_recipients(
        payload: EmailRecipientPreviewRequest,
        session=Depends(require_permission("email_use")),
    ) -> dict:
        _ = session
        if not payload.depot_ids:
            empty = {"count": 0, "recipients": [], "depot_names": []}
            if enable_web_features:
                empty["selected_contact_count"] = 0
            return empty
        recipients = repository.get_kontakte_by_depot_ids(payload.depot_ids)
        selected_contact_count = 0
        if enable_web_features and getattr(payload, "kontakt_ids", None):
            selected_ids = {int(item) for item in payload.kontakt_ids if int(item) > 0}
            selected_contact_count = len(selected_ids)
            recipients = [row for row in recipients if int(row.get("id") or 0) in selected_ids]
        depot_names = sorted({str(row["depot_name"]) for row in recipients})
        result = {
            "count": len(recipients),
            "recipients": recipients,
            "depot_names": depot_names,
        }
        if enable_web_features:
            result["selected_contact_count"] = selected_contact_count
        return result

    if enable_web_features:

        @router.get("/delivery/status")
        def get_email_delivery_status(
            session=Depends(require_permission("email_use")),
        ) -> dict[str, Any]:
            _ = session
            settings = get_email_delivery_settings()
            missing = email_delivery_missing_config(settings)
            return {
                "mode": settings.mode,
                "can_send_now": settings.mode == "smtp" and not missing,
                "from_address": settings.smtp_from_address,
                "from_name": settings.smtp_from_name,
                "missing_config": missing,
            }

    @router.post("/drafts", status_code=status.HTTP_201_CREATED)
    def create_email_draft(
        payload: EmailDraftCreateRequest,
        session=Depends(require_permission("email_use")),
    ) -> dict[str, Any]:
        _ = session
        if not payload.depot_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitte mindestens ein Depot auswaehlen.",
            )
        recipients = repository.get_kontakte_by_depot_ids(payload.depot_ids)
        if enable_web_features and getattr(payload, "kontakt_ids", None):
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

        if enable_web_features:
            send_now_requested = bool(getattr(payload, "send_now", False))
            delivery_status = "draft"
            delivery_error = ""
            smtp_result: dict[str, Any] = {}
            if send_now_requested:
                try:
                    smtp_result = send_email_via_smtp(
                        get_email_delivery_settings(),
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
                    "kontakt_ids": getattr(payload, "kontakt_ids", None),
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

        log_id = repository.add_email_verlauf(
            betreff=payload.betreff,
            nachricht=payload.nachricht or "",
            depot_names=", ".join(depot_names),
            emails="; ".join(unique_emails),
            anzahl=len(unique_emails),
        )
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="email",
            resource_id=log_id,
            details={"depot_ids": payload.depot_ids, "recipient_count": len(unique_emails)},
        )
        return {"id": log_id, "status": "draft_created", "recipient_count": len(unique_emails)}

    @router.get("/history")
    def list_email_history(
        limit: int = 50,
        session=Depends(require_permission("email_use")),
    ) -> list[dict]:
        _ = session
        return repository.get_email_verlauf(limit=limit)

    @router.get("/history/{email_id}")
    def get_email_history_detail(
        email_id: int,
        session=Depends(require_permission("email_use")),
    ) -> dict:
        _ = session
        details = repository.get_email_details(email_id)
        if details is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-Mail-Eintrag nicht gefunden.")
        return details

    if enable_web_features and EmailDeliveryStatusUpdateRequest is not None:

        @router.patch("/history/{email_id}/delivery-status")
        def update_email_history_delivery_status(
            email_id: int,
            payload: EmailDeliveryStatusUpdateRequest,
            session=Depends(require_permission("email_use")),
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

    return router
