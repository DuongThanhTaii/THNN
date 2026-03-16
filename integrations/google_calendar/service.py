"""Google Calendar integration service (initial scaffold)."""

from typing import Any

from config.settings import get_settings


class GoogleCalendarService:
    """Thin Google Calendar service placeholder for future full implementation."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client_id = settings.google_client_id
        self.redirect_uri = settings.google_redirect_uri

    def is_configured(self) -> bool:
        return bool(self.client_id and self.redirect_uri)

    def build_oauth_connect_payload(self) -> dict[str, Any]:
        return {
            "provider": "google_calendar",
            "configured": self.is_configured(),
            "redirect_uri": self.redirect_uri,
            "next_step": "Complete OAuth code exchange in callback endpoint.",
        }

    def normalize_webhook_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "google_calendar",
            "event_id": str(
                payload.get("resourceId") or payload.get("eventId") or "unknown"
            ),
            "type": str(payload.get("resourceState") or "unknown"),
            "payload": payload,
        }
