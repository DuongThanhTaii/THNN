"""Webhook endpoints for external integrations."""

import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from config.settings import get_settings
from integrations.google_calendar import GoogleCalendarService
from integrations.idempotency_registry import ProcessedEventRegistry
from integrations.jira import JiraService
from storage.db import get_db_cursor

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

MAX_WEBHOOK_RETRIES = 3


def _extract_signature_digest(value: str | None) -> str:
    if not value:
        return ""
    candidate = value.strip()
    if candidate.startswith("sha256="):
        candidate = candidate.split("=", 1)[1]
    return candidate.lower()


def _verify_jira_signature(raw_body: bytes, signature_header: str | None) -> bool:
    secret = get_settings().jira_webhook_secret.strip()
    if not secret:
        return True
    provided = _extract_signature_digest(signature_header)
    if not provided:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


def _verify_google_headers(
    *,
    x_goog_resource_id: str | None,
    x_goog_resource_state: str | None,
    x_goog_message_number: str | None,
    x_goog_channel_id: str | None,
    x_goog_channel_token: str | None,
) -> tuple[bool, str]:
    missing = [
        name
        for name, value in [
            ("x-goog-resource-id", x_goog_resource_id),
            ("x-goog-resource-state", x_goog_resource_state),
            ("x-goog-message-number", x_goog_message_number),
            ("x-goog-channel-id", x_goog_channel_id),
        ]
        if not value or not value.strip()
    ]
    if missing:
        return False, f"missing required google headers: {', '.join(missing)}"

    expected = get_settings().google_webhook_secret.strip()
    if expected:
        token = (x_goog_channel_token or "").strip()
        if token != expected:
            return False, "invalid google webhook token"
    return True, "ok"


def _build_internal_event(
    *,
    source: str,
    normalized: dict[str, Any],
    workspace_id: int,
    headers: dict[str, str],
) -> dict[str, Any]:
    payload = normalized.get("payload")
    stable_payload = payload if isinstance(payload, dict) else {"raw": payload}
    payload_hash = ProcessedEventRegistry.build_payload_hash(stable_payload)

    event_id = str(normalized.get("event_id") or "unknown")
    event_type = str(normalized.get("type") or "unknown")

    return {
        "id": f"{source}:{event_id}",
        "source": source,
        "event_id": event_id,
        "event_type": event_type,
        "workspace_id": workspace_id,
        "received_at": datetime.now(UTC).isoformat(),
        "payload_hash": payload_hash,
        "headers": headers,
        "payload": stable_payload,
    }


def _record_processed_event(event: dict[str, Any]) -> bool:
    status = ProcessedEventRegistry().register_event(
        source=event["source"],
        event_id=event["event_id"],
        payload_hash=event["payload_hash"],
    )
    return status == "processed"


def _record_dead_letter(
    *,
    source: str,
    event: dict[str, Any],
    error: str,
    attempts: int,
) -> None:
    database_url = get_settings().database_url.strip()
    if not database_url:
        return

    metadata = {
        "source": source,
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "payload_hash": event.get("payload_hash"),
        "attempts": attempts,
        "error": error,
    }
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs(workspace_id, action, resource_type, resource_id, metadata)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            """,
            (
                int(event.get("workspace_id") or 0) or None,
                "webhook.dead_letter",
                "webhook_event",
                str(event.get("id") or "unknown"),
                json.dumps(metadata),
            ),
        )


async def _process_with_retry(*, source: str, event: dict[str, Any]) -> dict[str, Any]:
    last_error = ""
    for attempt in range(1, MAX_WEBHOOK_RETRIES + 1):
        try:
            inserted = _record_processed_event(event)
            return {
                "status": "processed" if inserted else "duplicate",
                "attempts": attempt,
            }
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt < MAX_WEBHOOK_RETRIES:
                await asyncio.sleep(0.1 * attempt)

    _record_dead_letter(
        source=source,
        event=event,
        error=last_error or "unknown error",
        attempts=MAX_WEBHOOK_RETRIES,
    )
    raise HTTPException(
        status_code=502,
        detail=f"failed to process webhook after retries: {last_error or 'unknown error'}",
    )


@router.post("/jira")
async def jira_webhook(
    request: Request,
    payload: dict,
    x_atlassian_webhook_signature: str | None = Header(default=None),
    x_hook_secret: str | None = Header(default=None),
    x_workspace_id: int | None = Header(default=None),
) -> dict:
    settings = get_settings()
    expected = settings.jira_webhook_secret.strip()

    raw_body = await request.body()
    signature_ok = _verify_jira_signature(raw_body, x_atlassian_webhook_signature)
    legacy_secret_ok = bool(expected and x_hook_secret == expected)
    accepted = (not expected) or signature_ok or legacy_secret_ok
    if not accepted:
        raise HTTPException(status_code=401, detail="invalid jira webhook signature")

    service = JiraService()
    normalized = service.normalize_webhook_event(payload)
    workspace_id = x_workspace_id if x_workspace_id is not None else 1
    internal_event = _build_internal_event(
        source="jira",
        normalized=normalized,
        workspace_id=workspace_id,
        headers={
            "x-atlassian-webhook-signature": x_atlassian_webhook_signature or "",
        },
    )
    processing = await _process_with_retry(source="jira", event=internal_event)

    return {
        "accepted": accepted,
        "normalized": normalized,
        "internal_event": internal_event,
        "processing": processing,
    }


@router.post("/google-calendar")
async def google_calendar_webhook(
    payload: dict,
    x_goog_channel_id: str | None = Header(default=None),
    x_goog_channel_token: str | None = Header(default=None),
    x_goog_resource_id: str | None = Header(default=None),
    x_goog_resource_state: str | None = Header(default=None),
    x_goog_message_number: str | None = Header(default=None),
    x_hook_secret: str | None = Header(default=None),
    x_workspace_id: int | None = Header(default=None),
) -> dict:
    settings = get_settings()
    expected = settings.google_webhook_secret.strip()

    verified, reason = _verify_google_headers(
        x_goog_resource_id=x_goog_resource_id,
        x_goog_resource_state=x_goog_resource_state,
        x_goog_message_number=x_goog_message_number,
        x_goog_channel_id=x_goog_channel_id,
        x_goog_channel_token=x_goog_channel_token,
    )

    legacy_secret_ok = bool(expected and x_hook_secret == expected)
    accepted = verified or legacy_secret_ok
    if not accepted:
        raise HTTPException(status_code=401, detail=reason)

    enriched_payload = dict(payload)
    if "resourceId" not in enriched_payload and x_goog_resource_id:
        enriched_payload["resourceId"] = x_goog_resource_id
    if "resourceState" not in enriched_payload and x_goog_resource_state:
        enriched_payload["resourceState"] = x_goog_resource_state
    if "eventId" not in enriched_payload and x_goog_message_number:
        enriched_payload["eventId"] = x_goog_message_number

    service = GoogleCalendarService()
    normalized = service.normalize_webhook_event(enriched_payload)
    if x_goog_message_number:
        normalized["event_id"] = x_goog_message_number
    if x_goog_resource_state:
        normalized["type"] = f"google_calendar:{x_goog_resource_state}"
    workspace_id = x_workspace_id if x_workspace_id is not None else 1
    internal_event = _build_internal_event(
        source="google_calendar",
        normalized=normalized,
        workspace_id=workspace_id,
        headers={
            "x-goog-channel-id": x_goog_channel_id or "",
            "x-goog-resource-id": x_goog_resource_id or "",
            "x-goog-resource-state": x_goog_resource_state or "",
            "x-goog-message-number": x_goog_message_number or "",
        },
    )
    processing = await _process_with_retry(
        source="google_calendar",
        event=internal_event,
    )

    return {
        "accepted": accepted,
        "normalized": normalized,
        "internal_event": internal_event,
        "processing": processing,
    }
