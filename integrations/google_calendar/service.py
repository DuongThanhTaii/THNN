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

    def _http_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=self.http_read_timeout,
            connect=self.http_connect_timeout,
            write=self.http_write_timeout,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        url = f"https://www.googleapis.com/calendar/v3/{path.lstrip('/')}"
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
                detail=f"Google Calendar API request failed: {type(e).__name__}: {e}",
            ) from e

        if response.status_code >= 400:
            detail = response.text
            try:
                payload = response.json()
                error_obj = payload.get("error") if isinstance(payload, dict) else None
                detail = str(
                    (
                        error_obj.get("message")
                        if isinstance(error_obj, dict)
                        else payload
                    )
                    or response.text
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=502,
                detail=f"Google Calendar API error ({response.status_code}): {detail}",
            )

        if response.status_code == 204 or not response.content:
            return None
        data = response.json()
        if isinstance(data, (dict, list)):
            return data
        raise HTTPException(
            status_code=502,
            detail="Google Calendar API returned invalid payload",
        )

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

    async def list_calendars(self, access_token: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/users/me/calendarList",
            access_token=access_token,
        )
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Invalid calendar list payload")
        items = data.get("items", [])
        return [item for item in items if isinstance(item, dict)]

    async def list_events(
        self,
        access_token: str,
        calendar_id: str,
        *,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 50,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "maxResults": max_results,
            "singleEvents": str(single_events).lower(),
            "orderBy": order_by,
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        data = await self._request(
            "GET",
            f"/calendars/{calendar_id}/events",
            access_token=access_token,
            params=params,
        )
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Invalid events payload")
        items = data.get("items", [])
        return [item for item in items if isinstance(item, dict)]

    async def create_event(
        self,
        access_token: str,
        calendar_id: str,
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        data = await self._request(
            "POST",
            f"/calendars/{calendar_id}/events",
            access_token=access_token,
            json_data=event_payload,
        )
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Invalid create event payload")
        return data

    async def update_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        data = await self._request(
            "PATCH",
            f"/calendars/{calendar_id}/events/{event_id}",
            access_token=access_token,
            json_data=event_payload,
        )
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Invalid update event payload")
        return data

    async def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> None:
        await self._request(
            "DELETE",
            f"/calendars/{calendar_id}/events/{event_id}",
            access_token=access_token,
        )

    async def watch_events(
        self,
        access_token: str,
        calendar_id: str,
        *,
        channel_id: str,
        webhook_address: str,
        token: str | None = None,
        expiration_ms: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_address,
        }
        if token:
            body["token"] = token
        if expiration_ms is not None:
            body["expiration"] = expiration_ms

        data = await self._request(
            "POST",
            f"/calendars/{calendar_id}/events/watch",
            access_token=access_token,
            json_data=body,
        )
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=502, detail="Invalid watch response payload"
            )
        return data

    def normalize_webhook_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "google_calendar",
            "event_id": str(
                payload.get("resourceId") or payload.get("eventId") or "unknown"
            ),
            "type": str(payload.get("resourceState") or "unknown"),
            "payload": payload,
        }
