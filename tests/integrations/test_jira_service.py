from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from integrations.jira.service import JiraService


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
def jira_settings():
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


@pytest.mark.asyncio
async def test_list_projects_uses_cloud_api(monkeypatch, jira_settings):
    monkeypatch.setattr("integrations.jira.service.get_settings", lambda: jira_settings)

    captured: dict[str, object] = {}

    def responder(method: str, url: str, kwargs: dict):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        return _FakeResponse(200, {"values": [{"id": "100", "key": "DEMO"}]})

    monkeypatch.setattr(
        "integrations.jira.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = JiraService()
    projects = await svc.list_projects("token")

    assert projects == [{"id": "100", "key": "DEMO"}]
    assert captured["method"] == "GET"
    assert (
        captured["url"]
        == "https://api.atlassian.com/ex/jira/cloud-1/rest/api/3/project/search"
    )


@pytest.mark.asyncio
async def test_transition_issue_returns_none_for_204(monkeypatch, jira_settings):
    monkeypatch.setattr("integrations.jira.service.get_settings", lambda: jira_settings)

    def responder(method: str, url: str, kwargs: dict):
        assert method == "POST"
        assert url.endswith("/issue/ABC-7/transitions")
        assert kwargs["json"] == {"transition": {"id": "31"}}
        return _FakeResponse(204)

    monkeypatch.setattr(
        "integrations.jira.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = JiraService()
    result = await svc.transition_issue("token", "ABC-7", "31")

    assert result is None


@pytest.mark.asyncio
async def test_add_comment_raises_on_api_error(monkeypatch, jira_settings):
    monkeypatch.setattr("integrations.jira.service.get_settings", lambda: jira_settings)

    def responder(method: str, url: str, kwargs: dict):
        return _FakeResponse(400, {"message": "bad request"}, text="bad request")

    monkeypatch.setattr(
        "integrations.jira.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = JiraService()
    with pytest.raises(HTTPException) as exc:
        await svc.add_comment("token", "ABC-7", "hello")

    assert exc.value.status_code == 502
    assert "Jira API error" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_get_accessible_resources_returns_dict_list(monkeypatch, jira_settings):
    monkeypatch.setattr("integrations.jira.service.get_settings", lambda: jira_settings)

    def responder(method: str, url: str, kwargs: dict):
        return _FakeResponse(200, [{"id": "cloud-1"}, None])

    monkeypatch.setattr(
        "integrations.jira.service.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(responder=responder),
    )

    svc = JiraService()
    resources = await svc.get_accessible_resources("token")

    assert resources == [{"id": "cloud-1"}]
