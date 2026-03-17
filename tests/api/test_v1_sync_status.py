from contextlib import contextmanager
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routers import sync


def _make_client(monkeypatch, cur: MagicMock) -> TestClient:
    @contextmanager
    def fake_get_db_cursor():
        yield cur

    monkeypatch.setattr(sync, "get_db_cursor", fake_get_db_cursor)

    app = FastAPI()
    app.include_router(sync.router)
    return TestClient(app)


def test_sync_status_projection_degraded_with_open_conflicts(monkeypatch):
    cur = MagicMock()
    cur.fetchone.side_effect = [
        (3, 2),
        (2, 5, "2026-03-16T10:30:00+00:00"),
    ]
    cur.fetchall.return_value = [
        (
            9,
            "jira",
            "google_calendar",
            "OPS-17",
            "field mismatch: status",
            "open",
            "2026-03-16T10:30:00+00:00",
            None,
        )
    ]

    client = _make_client(monkeypatch, cur)
    response = client.get("/sync/status", params={"workspace_id": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["workspace_id"] == 1
    assert body["health"] == "degraded"
    assert body["policies_total"] == 3
    assert body["policies_enabled"] == 2
    assert body["conflicts_open"] == 2
    assert body["conflicts_resolved"] == 5
    assert len(body["recent_conflicts"]) == 1
    assert body["recent_conflicts"][0]["entity_ref"] == "OPS-17"


def test_sync_status_projection_idle_when_no_enabled_policy(monkeypatch):
    cur = MagicMock()
    cur.fetchone.side_effect = [
        (2, 0),
        (0, 0, None),
    ]
    cur.fetchall.return_value = []

    client = _make_client(monkeypatch, cur)
    response = client.get("/sync/status", params={"workspace_id": 22})

    assert response.status_code == 200
    body = response.json()
    assert body["health"] == "idle"
    assert body["recent_conflicts"] == []


def test_sync_status_projection_limits_recent_conflicts(monkeypatch):
    cur = MagicMock()
    cur.fetchone.side_effect = [
        (1, 1),
        (0, 1, "2026-03-16T12:00:00+00:00"),
    ]
    cur.fetchall.return_value = []

    client = _make_client(monkeypatch, cur)
    response = client.get(
        "/sync/status",
        params={"workspace_id": 7, "recent_limit": 999},
    )

    assert response.status_code == 200

    third_query_params = cur.execute.call_args_list[2].args[1]
    assert third_query_params == (7, 50)
