"""Integration endpoints for Jira and Google Calendar."""

from fastapi import APIRouter

from integrations.google_calendar import GoogleCalendarService
from integrations.jira import JiraService

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/jira/connect")
async def jira_connect_payload() -> dict:
    service = JiraService()
    return service.build_oauth_connect_payload()


@router.post("/jira/connect")
async def jira_connect() -> dict:
    service = JiraService()
    return service.build_oauth_connect_payload()


@router.get("/jira/callback")
async def jira_callback(code: str = "", state: str = "") -> dict:
    return {
        "provider": "jira",
        "status": "todo",
        "message": "Jira OAuth callback received. Token exchange implementation pending.",
        "has_code": bool(code),
        "state": state,
    }


@router.get("/google/connect")
async def google_connect_payload() -> dict:
    service = GoogleCalendarService()
    return service.build_oauth_connect_payload()


@router.post("/google/connect")
async def google_connect() -> dict:
    service = GoogleCalendarService()
    return service.build_oauth_connect_payload()


@router.get("/google/callback")
async def google_callback(code: str = "", state: str = "") -> dict:
    return {
        "provider": "google_calendar",
        "status": "todo",
        "message": "Google OAuth callback received. Token exchange implementation pending.",
        "has_code": bool(code),
        "state": state,
    }
