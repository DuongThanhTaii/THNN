"""Webhook endpoints for external integrations."""

from fastapi import APIRouter, Header

from config.settings import get_settings
from integrations.google_calendar import GoogleCalendarService
from integrations.jira import JiraService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/jira")
async def jira_webhook(
    payload: dict,
    x_hook_secret: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    expected = settings.jira_webhook_secret.strip()
    accepted = (not expected) or (x_hook_secret == expected)

    service = JiraService()
    normalized = service.normalize_webhook_event(payload)
    return {
        "accepted": accepted,
        "normalized": normalized,
    }


@router.post("/google-calendar")
async def google_calendar_webhook(
    payload: dict,
    x_hook_secret: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    expected = settings.google_webhook_secret.strip()
    accepted = (not expected) or (x_hook_secret == expected)

    service = GoogleCalendarService()
    normalized = service.normalize_webhook_event(payload)
    return {
        "accepted": accepted,
        "normalized": normalized,
    }
