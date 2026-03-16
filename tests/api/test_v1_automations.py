from contextlib import contextmanager
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routers import automations


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(automations.router)
    return TestClient(app)


def _mock_cursor(monkeypatch, cur: MagicMock) -> None:
    @contextmanager
    def fake_get_db_cursor():
        yield cur

    monkeypatch.setattr(automations, "get_db_cursor", fake_get_db_cursor)


def test_list_automations_returns_rows(monkeypatch):
    cur = MagicMock()
    cur.fetchall.return_value = [
        (3, 1, "Daily sync", "schedule", "sync", {"hour": 9}, True),
        (2, 1, "Urgent route", "event", "notify", {}, False),
    ]
    _mock_cursor(monkeypatch, cur)

    client = _make_client()
    response = client.get("/automations", params={"workspace_id": 1, "limit": 20})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["name"] == "Daily sync"
    assert body[0]["config"]["hour"] == 9


def test_create_automation_success(monkeypatch):
    cur = MagicMock()
    cur.fetchone.side_effect = [
        (1,),
        (10, 1, "Auto create", "event", "create_task", {"x": 1}, True),
    ]
    _mock_cursor(monkeypatch, cur)

    client = _make_client()
    response = client.post(
        "/automations",
        json={
            "workspace_id": 1,
            "name": "Auto create",
            "trigger_type": "event",
            "action_type": "create_task",
            "config": {"x": 1},
            "enabled": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == 10


def test_create_automation_workspace_not_found(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = None
    _mock_cursor(monkeypatch, cur)

    client = _make_client()
    response = client.post(
        "/automations",
        json={
            "workspace_id": 999,
            "name": "Auto create",
            "trigger_type": "event",
            "action_type": "create_task",
            "config": {},
            "enabled": True,
        },
    )

    assert response.status_code == 404
    assert "workspace not found" in response.json()["detail"]


def test_update_automation_no_fields_returns_400(monkeypatch):
    cur = MagicMock()
    _mock_cursor(monkeypatch, cur)

    client = _make_client()
    response = client.patch("/automations/1", json={"workspace_id": 1})

    assert response.status_code == 400
    assert "no fields to update" in response.json()["detail"]


def test_update_automation_success(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = (1, 1, "Renamed", "schedule", "sync", {}, False)
    _mock_cursor(monkeypatch, cur)

    client = _make_client()
    response = client.patch(
        "/automations/1",
        json={
            "workspace_id": 1,
            "name": "Renamed",
            "enabled": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["enabled"] is False


def test_delete_automation_not_found(monkeypatch):
    cur = MagicMock()
    cur.rowcount = 0
    _mock_cursor(monkeypatch, cur)

    client = _make_client()
    response = client.delete("/automations/5", params={"workspace_id": 1})

    assert response.status_code == 404
    assert "automation not found" in response.json()["detail"]


def test_delete_automation_success(monkeypatch):
    cur = MagicMock()
    cur.rowcount = 1
    _mock_cursor(monkeypatch, cur)

    client = _make_client()
    response = client.delete("/automations/5", params={"workspace_id": 1})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["deleted"] == 1
