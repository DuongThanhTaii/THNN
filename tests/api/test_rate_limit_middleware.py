from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.rate_limit import enforce_rate_limits


def _make_client(
    monkeypatch,
    *,
    enabled: bool,
    user_limit: int = 2,
    workspace_limit: int = 999,
    channel_limit: int = 999,
) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def rate_limit_middleware(request, call_next):
        return await enforce_rate_limits(request, call_next)

    @app.get("/api/v1/demo")
    async def demo():
        return {"status": "ok"}

    settings = SimpleNamespace(
        rate_limit_enforce=enabled,
        rate_limit_user_limit=user_limit,
        rate_limit_user_window=60,
        rate_limit_workspace_limit=workspace_limit,
        rate_limit_workspace_window=60,
        rate_limit_channel_limit=channel_limit,
        rate_limit_channel_window=60,
    )
    monkeypatch.setattr("api.rate_limit.get_settings", lambda: settings)
    return TestClient(app)


def test_rate_limit_disabled_allows_requests(monkeypatch):
    client = _make_client(monkeypatch, enabled=False, user_limit=1)

    r1 = client.get("/api/v1/demo", headers={"x-user-id": "u1"})
    r2 = client.get("/api/v1/demo", headers={"x-user-id": "u1"})

    assert r1.status_code == 200
    assert r2.status_code == 200


def test_rate_limit_enforced_per_user(monkeypatch):
    client = _make_client(monkeypatch, enabled=True, user_limit=2)

    r1 = client.get("/api/v1/demo", headers={"x-user-id": "u-limit"})
    r2 = client.get("/api/v1/demo", headers={"x-user-id": "u-limit"})
    r3 = client.get("/api/v1/demo", headers={"x-user-id": "u-limit"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    payload = r3.json()
    assert payload["error"]["scope"] == "user"


def test_rate_limit_scope_isolated_by_user(monkeypatch):
    client = _make_client(monkeypatch, enabled=True, user_limit=1)

    blocked = client.get("/api/v1/demo", headers={"x-user-id": "same"})
    blocked_2 = client.get("/api/v1/demo", headers={"x-user-id": "same"})
    other = client.get("/api/v1/demo", headers={"x-user-id": "other"})

    assert blocked.status_code == 200
    assert blocked_2.status_code == 429
    assert other.status_code == 200


def test_rate_limit_enforced_per_workspace_scope(monkeypatch):
    client = _make_client(
        monkeypatch,
        enabled=True,
        user_limit=999,
        workspace_limit=1,
    )

    r1 = client.get("/api/v1/demo", headers={"x-workspace-id": "w-limit"})
    r2 = client.get("/api/v1/demo", headers={"x-workspace-id": "w-limit"})

    assert r1.status_code == 200
    assert r2.status_code == 429
    payload = r2.json()
    assert payload["error"]["scope"] == "workspace"


def test_rate_limit_enforced_per_channel_scope(monkeypatch):
    client = _make_client(
        monkeypatch,
        enabled=True,
        user_limit=999,
        workspace_limit=999,
        channel_limit=1,
    )

    r1 = client.get("/api/v1/demo", headers={"x-channel-id": "c-limit"})
    r2 = client.get("/api/v1/demo", headers={"x-channel-id": "c-limit"})

    assert r1.status_code == 200
    assert r2.status_code == 429
    payload = r2.json()
    assert payload["error"]["scope"] == "channel"
