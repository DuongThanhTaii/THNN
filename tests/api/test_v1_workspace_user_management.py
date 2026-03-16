from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routers import users, workspaces


def _make_client(monkeypatch, cur: MagicMock) -> TestClient:
    @contextmanager
    def fake_get_db_cursor():
        yield cur

    monkeypatch.setattr(workspaces, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr(users, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr(workspaces, "publish_workspace_event", AsyncMock())

    app = FastAPI()
    app.include_router(workspaces.router)
    app.include_router(users.router)
    return TestClient(app)


def test_get_workspace_by_id(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = (7, "demo", "Demo Workspace", 2)
    client = _make_client(monkeypatch, cur)

    response = client.get("/workspaces/7")

    assert response.status_code == 200
    assert response.json()["id"] == 7
    assert response.json()["owner_user_id"] == 2


def test_update_workspace_requires_fields(monkeypatch):
    cur = MagicMock()
    client = _make_client(monkeypatch, cur)

    response = client.patch("/workspaces/7", json={})

    assert response.status_code == 400
    assert "no fields to update" in response.json()["detail"]


def test_update_workspace_success(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = (7, "demo-updated", "Updated", 3)
    client = _make_client(monkeypatch, cur)

    response = client.patch(
        "/workspaces/7",
        json={"name": "Updated", "slug": "Demo-Updated", "owner_user_id": 3},
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "demo-updated"
    assert response.json()["name"] == "Updated"


def test_list_users(monkeypatch):
    cur = MagicMock()
    cur.fetchall.return_value = [
        (4, "ext-4", "u4@example.com", "User 4"),
        (3, None, "u3@example.com", "User 3"),
    ]
    client = _make_client(monkeypatch, cur)

    response = client.get("/users", params={"limit": 20})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["id"] == 4


def test_get_user_not_found(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = None
    client = _make_client(monkeypatch, cur)

    response = client.get("/users/99")

    assert response.status_code == 404
    assert "user not found" in response.json()["detail"]


def test_create_user_upsert(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = (11, "ext-11", "new@example.com", "New User")
    client = _make_client(monkeypatch, cur)

    response = client.post(
        "/users",
        json={
            "email": "NEW@example.com",
            "display_name": "New User",
            "external_id": "ext-11",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"


def test_update_user_success(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = (11, "ext-11-up", "new@example.com", "New User Up")
    client = _make_client(monkeypatch, cur)

    response = client.patch(
        "/users/11",
        json={"display_name": "New User Up", "external_id": "ext-11-up"},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "New User Up"
