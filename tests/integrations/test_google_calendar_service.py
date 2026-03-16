from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from integrations.google_calendar.service import GoogleCalendarService


class _FakeResponse:
    def __init__(self, status_code: int, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        if status_code == 204 or json_data is None:
            self.content = b""
        else:
            self.content = b"{}"

    def json(self):
        return self._json_data


class _FakeAsyncClient:
    def __init__(self, *, responder):
        self._responder = responder

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def request(self, method: str, url: str, **kwargs):
        return self._responder(method, url, kwargs)

    async def get(self, url: str, **kwargs):
        return self._responder("GET", url, kwargs)

    async def post(self, url: str, **kwargs):
        return self._responder("POST", url, kwargs)


@pytest.fixture
def google_settings():
    return SimpleNamespace(
        google_client_id="gid",
        google_client_secret="gsecret",
        google_redirect_uri="http://localhost:8082/api/v1/integrations/google/callback",
        google_oauth_scopes="openid email profile https://www.googleapis.com/auth/calendar",
        http_read_timeout=30.0,
        http_write_timeout=10.0,
        http_connect_timeout=5.0,
    )


@pytest.mark.asyncio
async def test_list_events_passes_query_params(monkeypatch, google_settings):
    monkeypatch.setattr(
        "integrations.google_calendar.service.get_settings", lambda: google_settings
    )

    captured: dict[str, object] = {}

    def responder(method: str, url: str, kwargs: dict):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return _FakeResponse(200, {"items": [{"id": "evt-1"}]})

    monkeypatch.setattr(
        "integrations.google_calendar.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = GoogleCalendarService()
    events = await svc.list_events(
        "token",
        "primary",
        time_min="2026-01-01T00:00:00Z",
        max_results=10,
    )

    assert events == [{"id": "evt-1"}]
    assert captured["method"] == "GET"
    assert (
        captured["url"]
        == "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    )
    assert captured["params"] == {
        "maxResults": 10,
        "singleEvents": "true",
        "orderBy": "startTime",
        "timeMin": "2026-01-01T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_create_event_returns_payload(monkeypatch, google_settings):
    monkeypatch.setattr(
        "integrations.google_calendar.service.get_settings", lambda: google_settings
    )

    def responder(method: str, url: str, kwargs: dict):
        assert method == "POST"
        assert url.endswith("/calendars/primary/events")
        assert kwargs["json"] == {"summary": "Daily sync"}
        return _FakeResponse(200, {"id": "evt-99", "summary": "Daily sync"})

    monkeypatch.setattr(
        "integrations.google_calendar.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = GoogleCalendarService()
    event = await svc.create_event("token", "primary", {"summary": "Daily sync"})

    assert event["id"] == "evt-99"


@pytest.mark.asyncio
async def test_delete_event_handles_204(monkeypatch, google_settings):
    monkeypatch.setattr(
        "integrations.google_calendar.service.get_settings", lambda: google_settings
    )

    def responder(method: str, url: str, kwargs: dict):
        assert method == "DELETE"
        assert url.endswith("/calendars/primary/events/evt-7")
        return _FakeResponse(204)

    monkeypatch.setattr(
        "integrations.google_calendar.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = GoogleCalendarService()
    result = await svc.delete_event("token", "primary", "evt-7")

    assert result is None


@pytest.mark.asyncio
async def test_watch_events_sends_webhook_body(monkeypatch, google_settings):
    monkeypatch.setattr(
        "integrations.google_calendar.service.get_settings", lambda: google_settings
    )

    def responder(method: str, url: str, kwargs: dict):
        assert method == "POST"
        assert url.endswith("/calendars/primary/events/watch")
        assert kwargs["json"] == {
            "id": "ch-1",
            "type": "web_hook",
            "address": "https://callback.example.com/google",
            "token": "verify-token",
            "expiration": 999999,
        }
        return _FakeResponse(200, {"resourceId": "resource-1"})

    monkeypatch.setattr(
        "integrations.google_calendar.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = GoogleCalendarService()
    payload = await svc.watch_events(
        "token",
        "primary",
        channel_id="ch-1",
        webhook_address="https://callback.example.com/google",
        token="verify-token",
        expiration_ms=999999,
    )

    assert payload["resourceId"] == "resource-1"


@pytest.mark.asyncio
async def test_list_calendars_raises_on_api_error(monkeypatch, google_settings):
    monkeypatch.setattr(
        "integrations.google_calendar.service.get_settings", lambda: google_settings
    )

    def responder(method: str, url: str, kwargs: dict):
        return _FakeResponse(
            403,
            {"error": {"message": "forbidden"}},
            text="forbidden",
        )

    monkeypatch.setattr(
        "integrations.google_calendar.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = GoogleCalendarService()
    with pytest.raises(HTTPException) as exc:
        await svc.list_calendars("token")

    assert exc.value.status_code == 502
    assert "Google Calendar API error" in str(exc.value.detail)
