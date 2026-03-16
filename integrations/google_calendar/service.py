"""Google Calendar integration service (initial scaffold)."""

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from config.settings import get_settings


class GoogleCalendarService:
    """Thin Google Calendar service placeholder for future full implementation."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        self.oauth_scopes = settings.google_oauth_scopes
        self.auth_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.http_read_timeout = settings.http_read_timeout
        self.http_write_timeout = settings.http_write_timeout
        self.http_connect_timeout = settings.http_connect_timeout

    def is_configured(self) -> bool:
        return bool(
            self.client_id
            and self.client_secret
            and self.redirect_uri
            and self.oauth_scopes
        )

    def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.oauth_scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.auth_base_url}?{urlencode(params)}"

    def build_oauth_connect_payload(self, state: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": "google_calendar",
            "configured": self.is_configured(),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        if payload["configured"]:
            payload["authorization_url"] = self.build_authorization_url(state)
            payload["next_step"] = "Open authorization_url and complete OAuth consent."
        else:
            payload["authorization_url"] = None
            payload["next_step"] = "Configure Google OAuth env vars and retry."
        return payload

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        if not self.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Google OAuth is not configured (missing client, secret, redirect, or scopes)",
            )

        timeout = httpx.Timeout(
            timeout=self.http_read_timeout,
            connect=self.http_connect_timeout,
            write=self.http_write_timeout,
        )
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.token_url,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data=payload,
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Google OAuth token exchange failed: {type(e).__name__}: {e}",
            ) from e

        if response.status_code >= 400:
            detail = response.text
            try:
                err = response.json()
                detail = str(
                    err.get("error_description") or err.get("error") or response.text
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=502,
                detail=f"Google OAuth token endpoint rejected request: {detail}",
            )

        try:
            token_data = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Google OAuth token endpoint returned invalid JSON: {e}",
            ) from e

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=502,
                detail="Google OAuth token response missing access_token",
            )
        return token_data

    def normalize_webhook_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "google_calendar",
            "event_id": str(
                payload.get("resourceId") or payload.get("eventId") or "unknown"
            ),
            "type": str(payload.get("resourceState") or "unknown"),
            "payload": payload,
        }
