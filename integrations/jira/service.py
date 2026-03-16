"""Jira integration service (initial scaffold)."""

from typing import Any

from config.settings import get_settings


class JiraService:
    """Thin Jira service placeholder for future full implementation."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.jira_base_url
        self.client_id = settings.jira_client_id

    def is_configured(self) -> bool:
        return bool(self.base_url and self.client_id)

    def build_oauth_connect_payload(self) -> dict[str, Any]:
        return {
            "provider": "jira",
            "configured": self.is_configured(),
            "base_url": self.base_url,
            "next_step": "Complete OAuth handshake in dedicated callback endpoint.",
        }

    def normalize_webhook_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "jira",
            "event_id": str(
                payload.get("timestamp") or payload.get("webhookEvent") or "unknown"
            ),
            "type": str(payload.get("webhookEvent") or "unknown"),
            "payload": payload,
        }
