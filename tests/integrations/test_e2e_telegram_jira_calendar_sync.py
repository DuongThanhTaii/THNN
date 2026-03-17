from types import SimpleNamespace

import pytest

from integrations.google_calendar.service import GoogleCalendarService
from integrations.jira.service import JiraService
from integrations.sync_mapping import SyncMappingService
from messaging.models import IncomingMessage


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


def _jira_settings():
    return SimpleNamespace(
        jira_base_url="https://jira.example.com",
        jira_client_id="jid",
        jira_client_secret="jsecret",
        jira_cloud_id="cloud-1",
        jira_redirect_uri="http://localhost:8082/api/v1/integrations/jira/callback",
        jira_oauth_scopes="read:jira-user read:jira-work offline_access",
        jira_auth_audience="api.atlassian.com",
        http_read_timeout=30.0,
        http_write_timeout=10.0,
        http_connect_timeout=5.0,
    )


def _google_settings():
    return SimpleNamespace(
        google_client_id="gid",
        google_client_secret="gsecret",
        google_redirect_uri="http://localhost:8082/api/v1/integrations/google/callback",
        google_oauth_scopes="openid email profile https://www.googleapis.com/auth/calendar",
        http_read_timeout=30.0,
        http_write_timeout=10.0,
        http_connect_timeout=5.0,
    )


def _map_telegram_message_to_jira_fields(incoming: IncomingMessage) -> dict:
    summary = incoming.text.split("|", 1)[0].strip() or "Untitled task"
    return {
        "project": {"key": "OPS"},
        "issuetype": {"name": "Task"},
        "summary": summary,
        "description": f"Created from Telegram message {incoming.message_id}",
        "duedate": "2026-03-20",
    }


@pytest.mark.asyncio
async def test_e2e_telegram_to_jira_to_calendar_sync_flow(monkeypatch):
    monkeypatch.setattr("integrations.jira.service.get_settings", _jira_settings)
    monkeypatch.setattr(
        "integrations.google_calendar.service.get_settings", _google_settings
    )

    captured = {
        "jira_request": None,
        "calendar_request": None,
    }

    def responder(method: str, url: str, kwargs: dict):
        if "/rest/api/3/issue" in url:
            captured["jira_request"] = {
                "method": method,
                "url": url,
                "json": kwargs.get("json"),
            }
            return _FakeResponse(
                200,
                {
                    "id": "10011",
                    "key": "OPS-311",
                    "fields": {
                        "summary": kwargs["json"]["fields"]["summary"],
                        "description": kwargs["json"]["fields"]["description"],
                        "duedate": kwargs["json"]["fields"]["duedate"],
                        "status": {"name": "To Do"},
                        "priority": {"name": "Medium"},
                    },
                },
            )

        if "/calendar/v3/calendars/primary/events" in url:
            captured["calendar_request"] = {
                "method": method,
                "url": url,
                "json": kwargs.get("json"),
            }
            payload = dict(kwargs["json"])
            payload["id"] = "evt-311"
            return _FakeResponse(200, payload)

        return _FakeResponse(404, {"message": f"unexpected URL: {url}"})

    monkeypatch.setattr(
        "integrations.jira.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )
    monkeypatch.setattr(
        "integrations.google_calendar.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    telegram_msg = IncomingMessage(
        text="Deploy release v1.4.0 | assign @ops",
        chat_id="tg-chat-01",
        user_id="tg-user-09",
        message_id="tg-msg-501",
        platform="telegram",
    )

    jira = JiraService()
    mapper = SyncMappingService(default_timezone="Asia/Ho_Chi_Minh")
    gcal = GoogleCalendarService()

    issue = await jira.create_issue(
        "jira-token",
        _map_telegram_message_to_jira_fields(telegram_msg),
    )
    calendar_payload = mapper.map_jira_issue_to_calendar_event(issue)
    calendar_event = await gcal.create_event("google-token", "primary", calendar_payload)

    assert captured["jira_request"]["method"] == "POST"
    assert captured["jira_request"]["url"].endswith("/rest/api/3/issue")
    assert (
        captured["jira_request"]["json"]["fields"]["summary"]
        == "Deploy release v1.4.0"
    )

    assert captured["calendar_request"]["method"] == "POST"
    assert captured["calendar_request"]["url"].endswith("/calendar/v3/calendars/primary/events")
    assert (
        captured["calendar_request"]["json"]["extendedProperties"]["private"][
            "jiraKey"
        ]
        == "OPS-311"
    )
    assert captured["calendar_request"]["json"]["start"] == {"date": "2026-03-20"}
    assert captured["calendar_request"]["json"]["end"] == {"date": "2026-03-21"}

    assert issue["key"] == "OPS-311"
    assert calendar_event["id"] == "evt-311"