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
        self.cloud_id = settings.jira_cloud_id
        self.redirect_uri = settings.jira_redirect_uri
        self.oauth_scopes = settings.jira_oauth_scopes
        self.auth_audience = settings.jira_auth_audience
        self.auth_base_url = "https://auth.atlassian.com"
        self.http_read_timeout = settings.http_read_timeout
        self.http_write_timeout = settings.http_write_timeout
        self.http_connect_timeout = settings.http_connect_timeout

    def _http_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=self.http_read_timeout,
            connect=self.http_connect_timeout,
            write=self.http_write_timeout,
        )

    def _build_api_base(self, cloud_id: str | None = None) -> str:
        resolved_cloud_id = (cloud_id or self.cloud_id).strip()
        if resolved_cloud_id:
            return f"https://api.atlassian.com/ex/jira/{resolved_cloud_id}/rest/api/3"
        if self.base_url.strip():
            return f"{self.base_url.rstrip('/')}/rest/api/3"
        raise HTTPException(
            status_code=503,
            detail="Jira API base is not configured (missing JIRA_BASE_URL or JIRA_CLOUD_ID)",
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        cloud_id: str | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        base = self._build_api_base(cloud_id)
        url = f"{base}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout()) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Jira API request failed: {type(e).__name__}: {e}",
            ) from e

        if response.status_code >= 400:
            detail = response.text
            try:
                payload = response.json()
                detail = str(
                    payload.get("errorMessages") or payload.get("message") or payload
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=502,
                detail=f"Jira API error ({response.status_code}): {detail}",
            )

        if response.status_code == 204 or not response.content:
            return None
        data = response.json()
        if isinstance(data, (dict, list)):
            return data
        raise HTTPException(status_code=502, detail="Jira API returned invalid payload")

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
        timeout = self._http_timeout()
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

    async def get_accessible_resources(self, access_token: str) -> list[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._http_timeout()) as client:
                response = await client.get(
                    "https://api.atlassian.com/oauth/token/accessible-resources",
                    headers=headers,
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Jira accessible-resources request failed: {type(e).__name__}: {e}",
            ) from e

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Jira accessible-resources failed with status {response.status_code}",
            )
        data = response.json()
        if not isinstance(data, list):
            raise HTTPException(
                status_code=502, detail="Invalid Jira resources payload"
            )
        return [x for x in data if isinstance(x, dict)]

    async def list_projects(
        self,
        access_token: str,
        *,
        cloud_id: str | None = None,
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/project/search",
            access_token=access_token,
            cloud_id=cloud_id,
        )
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Invalid Jira projects payload")
        values = data.get("values", [])
        return [x for x in values if isinstance(x, dict)]

    async def get_issue(
        self,
        access_token: str,
        issue_key: str,
        *,
        cloud_id: str | None = None,
        expand: str | None = None,
    ) -> dict[str, Any]:
        params = {"expand": expand} if expand else None
        data = await self._request(
            "GET",
            f"/issue/{issue_key}",
            access_token=access_token,
            cloud_id=cloud_id,
            params=params,
        )
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Invalid Jira issue payload")
        return data

    async def create_issue(
        self,
        access_token: str,
        fields: dict[str, Any],
        *,
        cloud_id: str | None = None,
    ) -> dict[str, Any]:
        data = await self._request(
            "POST",
            "/issue",
            access_token=access_token,
            cloud_id=cloud_id,
            json_data={"fields": fields},
        )
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=502, detail="Invalid Jira create issue payload"
            )
        return data

    async def transition_issue(
        self,
        access_token: str,
        issue_key: str,
        transition_id: str,
        *,
        cloud_id: str | None = None,
    ) -> None:
        await self._request(
            "POST",
            f"/issue/{issue_key}/transitions",
            access_token=access_token,
            cloud_id=cloud_id,
            json_data={"transition": {"id": transition_id}},
        )

    async def add_comment(
        self,
        access_token: str,
        issue_key: str,
        body: str,
        *,
        cloud_id: str | None = None,
    ) -> dict[str, Any]:
        data = await self._request(
            "POST",
            f"/issue/{issue_key}/comment",
            access_token=access_token,
            cloud_id=cloud_id,
            json_data={"body": body},
        )
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Invalid Jira comment payload")
        return data

    def normalize_webhook_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "jira",
            "event_id": str(
                payload.get("timestamp") or payload.get("webhookEvent") or "unknown"
            ),
            "type": str(payload.get("webhookEvent") or "unknown"),
            "payload": payload,
        }
