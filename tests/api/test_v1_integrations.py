from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.v1.routers import integrations


def _make_settings() -> SimpleNamespace:
    return SimpleNamespace(jwt_secret="test-jwt-secret", encryption_master_key="")


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(integrations.router)
    return TestClient(app)


def test_jira_connect_builds_signed_state(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    captured: dict[str, str] = {}

    class FakeJiraService:
        def build_oauth_connect_payload(self, state: str) -> dict:
            captured["state"] = state
            return {
                "provider": "jira",
                "configured": True,
                "authorization_url": "https://auth.example/authorize",
                "next_step": "Open authorization_url and complete OAuth consent.",
            }

    monkeypatch.setattr(integrations, "JiraService", FakeJiraService)

    client = _make_client()
    response = client.get("/integrations/jira/connect", params={"workspace_id": 42})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "jira"
    assert body["workspace_id"] == 42

    state_payload = integrations._validate_oauth_state(captured["state"], "jira")
    assert state_payload["workspace_id"] == 42


def test_jira_callback_exchanges_code_and_persists_account(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    state = integrations._build_oauth_state("jira", 7)

    class FakeJiraService:
        async def exchange_code_for_tokens(self, code: str) -> dict:
            assert code == "abc"
            return {
                "access_token": "jira_access_token",
                "refresh_token": "jira_refresh_token",
                "expires_in": 3600,
                "scope": "read:jira-user",
                "token_type": "Bearer",
            }

    captured: dict = {}

    def fake_upsert(**kwargs) -> int:
        captured.update(kwargs)
        return 99

    monkeypatch.setattr(integrations, "JiraService", FakeJiraService)
    monkeypatch.setattr(integrations, "_upsert_integration_account", fake_upsert)

    client = _make_client()
    response = client.get(
        "/integrations/jira/callback",
        params={"code": "abc", "state": state},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["integration_id"] == 99
    assert body["workspace_id"] == 7

    assert captured["workspace_id"] == 7
    assert captured["provider"] == "jira"
    assert captured["access_token"] == "jira_access_token"
    assert captured["refresh_token"] == "jira_refresh_token"
    assert captured["token_expires_at"] is not None


def test_jira_callback_rejects_missing_state(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    client = _make_client()
    response = client.get("/integrations/jira/callback", params={"code": "abc"})

    assert response.status_code == 400
    assert "missing oauth state" in response.json()["detail"]


def test_jira_callback_rejects_wrong_provider_state(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    state = integrations._build_oauth_state("google_calendar", 3)

    class FakeJiraService:
        async def exchange_code_for_tokens(self, code: str) -> dict:
            return {"access_token": "x"}

    monkeypatch.setattr(integrations, "JiraService", FakeJiraService)

    client = _make_client()
    response = client.get(
        "/integrations/jira/callback",
        params={"code": "abc", "state": state},
    )

    assert response.status_code == 400
    assert "invalid oauth state provider" in response.json()["detail"]


def test_jira_callback_propagates_exchange_errors(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    state = integrations._build_oauth_state("jira", 9)

    class FakeJiraService:
        async def exchange_code_for_tokens(self, code: str) -> dict:
            raise HTTPException(status_code=502, detail="token exchange failed")

    monkeypatch.setattr(integrations, "JiraService", FakeJiraService)

    client = _make_client()
    response = client.get(
        "/integrations/jira/callback",
        params={"code": "abc", "state": state},
    )

    assert response.status_code == 502
    assert "token exchange failed" in response.json()["detail"]


def test_google_connect_builds_signed_state(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    captured: dict[str, str] = {}

    class FakeGoogleService:
        def build_oauth_connect_payload(self, state: str) -> dict:
            captured["state"] = state
            return {
                "provider": "google_calendar",
                "configured": True,
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "next_step": "Open authorization_url and complete OAuth consent.",
            }

    monkeypatch.setattr(integrations, "GoogleCalendarService", FakeGoogleService)

    client = _make_client()
    response = client.get("/integrations/google/connect", params={"workspace_id": 52})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "google_calendar"
    assert body["workspace_id"] == 52

    state_payload = integrations._validate_oauth_state(
        captured["state"], "google_calendar"
    )
    assert state_payload["workspace_id"] == 52


def test_google_callback_exchanges_code_and_persists_account(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    state = integrations._build_oauth_state("google_calendar", 11)

    class FakeGoogleService:
        async def exchange_code_for_tokens(self, code: str) -> dict:
            assert code == "xyz"
            return {
                "access_token": "google_access_token",
                "refresh_token": "google_refresh_token",
                "expires_in": 1800,
                "scope": "openid email profile",
                "token_type": "Bearer",
            }

    captured: dict = {}

    def fake_upsert(**kwargs) -> int:
        captured.update(kwargs)
        return 199

    monkeypatch.setattr(integrations, "GoogleCalendarService", FakeGoogleService)
    monkeypatch.setattr(integrations, "_upsert_integration_account", fake_upsert)

    client = _make_client()
    response = client.get(
        "/integrations/google/callback",
        params={"code": "xyz", "state": state},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["integration_id"] == 199
    assert body["workspace_id"] == 11

    assert captured["workspace_id"] == 11
    assert captured["provider"] == "google_calendar"
    assert captured["access_token"] == "google_access_token"
    assert captured["refresh_token"] == "google_refresh_token"
    assert captured["token_expires_at"] is not None


def test_google_callback_rejects_wrong_provider_state(monkeypatch):
    monkeypatch.setattr(integrations, "get_settings", _make_settings)

    state = integrations._build_oauth_state("jira", 5)

    class FakeGoogleService:
        async def exchange_code_for_tokens(self, code: str) -> dict:
            return {"access_token": "x"}

    monkeypatch.setattr(integrations, "GoogleCalendarService", FakeGoogleService)

    client = _make_client()
    response = client.get(
        "/integrations/google/callback",
        params={"code": "abc", "state": state},
    )

    assert response.status_code == 400
    assert "invalid oauth state provider" in response.json()["detail"]
