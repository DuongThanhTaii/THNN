from contextlib import contextmanager
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routers import automations, tasks, workspaces


def _make_client(monkeypatch, *, enabled: bool) -> TestClient:
    app = FastAPI()

    from api.rbac import enforce_rbac

    @app.middleware("http")
    async def rbac_middleware(request, call_next):
        return await enforce_rbac(request, call_next)

    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(automations.router, prefix="/api/v1")
    app.include_router(workspaces.router, prefix="/api/v1")

    settings = MagicMock()
    settings.rbac_enforce = enabled
    monkeypatch.setattr("api.rbac.get_settings", lambda: settings)

    cur = MagicMock()
    cur.fetchall.return_value = []

    @contextmanager
    def fake_get_db_cursor():
        yield cur

    monkeypatch.setattr(tasks, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr(automations, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr(workspaces, "get_db_cursor", fake_get_db_cursor)

    return TestClient(app)


def test_rbac_disabled_allows_requests_without_headers(monkeypatch):
    client = _make_client(monkeypatch, enabled=False)
    response = client.get("/api/v1/tasks", params={"workspace_id": 1})
    assert response.status_code == 200


def test_rbac_enabled_requires_role_header(monkeypatch):
    client = _make_client(monkeypatch, enabled=True)
    response = client.get("/api/v1/tasks", params={"workspace_id": 1})
    assert response.status_code == 401
    assert "x-user-role" in response.json()["detail"]


def test_rbac_enabled_rejects_insufficient_role(monkeypatch):
    client = _make_client(monkeypatch, enabled=True)
    response = client.post(
        "/api/v1/tasks",
        headers={
            "x-user-role": "viewer",
            "x-workspace-id": "1",
        },
        json={
            "workspace_id": 1,
            "title": "T1",
            "description": "x",
        },
    )
    assert response.status_code == 403


def test_rbac_enabled_enforces_workspace_scope(monkeypatch):
    client = _make_client(monkeypatch, enabled=True)
    response = client.get(
        "/api/v1/automations",
        params={"workspace_id": 2},
        headers={
            "x-user-role": "admin",
            "x-workspace-id": "1",
        },
    )
    assert response.status_code == 403
    assert "workspace scope mismatch" in response.json()["detail"]


def test_rbac_enabled_accepts_valid_role_and_scope(monkeypatch):
    client = _make_client(monkeypatch, enabled=True)
    response = client.get(
        "/api/v1/tasks",
        params={"workspace_id": 1},
        headers={
            "x-user-role": "member",
            "x-workspace-id": "1",
        },
    )
    assert response.status_code == 200


def test_rbac_workspace_create_requires_admin_or_owner(monkeypatch):
    client = _make_client(monkeypatch, enabled=True)

    denied = client.post(
        "/api/v1/workspaces",
        headers={"x-user-role": "member"},
        json={
            "slug": "demo-space",
            "name": "Demo",
            "owner_email": "owner@example.com",
            "owner_display_name": "Owner",
        },
    )
    assert denied.status_code == 403

    allowed = client.post(
        "/api/v1/workspaces",
        headers={"x-user-role": "owner"},
        json={
            "slug": "demo-space",
            "name": "Demo",
            "owner_email": "owner@example.com",
            "owner_display_name": "Owner",
        },
    )
    # This request gets past RBAC. Downstream may fail due to mocked DB row shape.
    assert allowed.status_code in {200, 500}
