"""Jira integration service (initial scaffold)."""

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from config.settings import get_settings


class JiraService:
    """Thin Jira service placeholder for future full implementation."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.jira_base_url
        self.client_id = settings.jira_client_id
        self.client_secret = settings.jira_client_secret
        self.redirect_uri = settings.jira_redirect_uri
        self.oauth_scopes = settings.jira_oauth_scopes
        self.auth_audience = settings.jira_auth_audience
        self.auth_base_url = "https://auth.atlassian.com"
        self.http_read_timeout = settings.http_read_timeout
        self.http_write_timeout = settings.http_write_timeout
        self.http_connect_timeout = settings.http_connect_timeout

    def is_configured(self) -> bool:
        return bool(
            self.base_url
            and self.client_id
            and self.client_secret
            and self.redirect_uri
            and self.oauth_scopes
        )

    def build_authorization_url(self, state: str) -> str:
        params = {
            "audience": self.auth_audience,
            "client_id": self.client_id,
            "scope": self.oauth_scopes,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        return f"{self.auth_base_url}/authorize?{urlencode(params)}"

    def build_oauth_connect_payload(self, state: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": "jira",
            "configured": self.is_configured(),
            "base_url": self.base_url,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        if payload["configured"]:
            payload["authorization_url"] = self.build_authorization_url(state)
            payload["next_step"] = "Open authorization_url and complete OAuth consent."
        else:
            payload["authorization_url"] = None
            payload["next_step"] = "Configure Jira OAuth env vars and retry."
        return payload

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        if not self.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Jira OAuth is not configured (missing base URL, client, secret, redirect, or scopes)",
            )

        token_url = f"{self.auth_base_url}/oauth/token"
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
                    token_url,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Jira OAuth token exchange failed: {type(e).__name__}: {e}",
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
                detail=f"Jira OAuth token endpoint rejected request: {detail}",
            )

        try:
            token_data = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Jira OAuth token endpoint returned invalid JSON: {e}",
            ) from e

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=502,
                detail="Jira OAuth token response missing access_token",
            )
        return token_data

    def normalize_webhook_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "jira",
            "event_id": str(
                payload.get("timestamp") or payload.get("webhookEvent") or "unknown"
            ),
            "type": str(payload.get("webhookEvent") or "unknown"),
            "payload": payload,
        }
