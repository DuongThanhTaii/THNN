import json
from contextlib import contextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routers import webhooks


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(webhooks.router)
    return TestClient(app)


def _settings(*, jira_secret: str = "", google_secret: str = "", database_url: str = ""):
    return SimpleNamespace(
        jira_webhook_secret=jira_secret,
        google_webhook_secret=google_secret,
        database_url=database_url,
    )


class _FakeWebhookCursor:
    def __init__(self, state: dict):
        self._state = state
        self.rowcount = 0
        self._fetchone_result = None

    def execute(self, sql, params=None):
        query = " ".join(str(sql).lower().split())
        params = params or ()

        if "insert into processed_events" in query:
            if self._state["fail_processed_event"]:
                raise RuntimeError("processed_events write failed")
            source, event_id, payload_hash = params
            key = (str(source), str(event_id))
            if key in self._state["processed_events"]:
                self.rowcount = 0
            else:
                self._state["processed_events"][key] = str(payload_hash)
                self.rowcount = 1
            return

        if "select payload_hash" in query and "from processed_events" in query:
            source, event_id = params
            key = (str(source), str(event_id))
            existing = self._state["processed_events"].get(key)
            self._fetchone_result = (existing,) if existing else None
            return

        if "insert into audit_logs" in query:
            self._state["audit_logs"].append(
                {
                    "workspace_id": params[0],
                    "action": params[1],
                    "resource_type": params[2],
                    "resource_id": params[3],
                    "metadata": json.loads(params[4]),
                }
            )
            self.rowcount = 1
            return

        raise AssertionError(f"Unexpected SQL in webhook flow integration test: {sql}")

    def fetchone(self):
        return self._fetchone_result


def _make_fake_db(*, fail_processed_event: bool = False):
    state = {
        "processed_events": {},
        "audit_logs": [],
        "fail_processed_event": fail_processed_event,
    }

    @contextmanager
    def _fake_get_db_cursor():
        yield _FakeWebhookCursor(state)

    return state, _fake_get_db_cursor


def test_jira_webhook_flow_persists_event_and_marks_duplicate(monkeypatch):
    state, fake_get_db_cursor = _make_fake_db()

    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(jira_secret="jira-secret", database_url="postgres://demo"),
    )
    monkeypatch.setattr("integrations.idempotency_registry.get_settings", webhooks.get_settings)
    monkeypatch.setattr(webhooks, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr("integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor)

    client = _make_client()
    payload = {"timestamp": 1710672000, "webhookEvent": "jira:issue_updated"}

    first = client.post("/webhooks/jira", json=payload, headers={"x-hook-secret": "jira-secret"})
    second = client.post("/webhooks/jira", json=payload, headers={"x-hook-secret": "jira-secret"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["processing"]["status"] == "processed"
    assert second.json()["processing"]["status"] == "duplicate"
    assert ("jira", "1710672000") in state["processed_events"]
    assert state["audit_logs"] == []


def test_google_webhook_flow_writes_dead_letter_after_retry_exhausted(monkeypatch):
    state, fake_get_db_cursor = _make_fake_db(fail_processed_event=True)

    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(google_secret="google-token", database_url="postgres://demo"),
    )
    monkeypatch.setattr("integrations.idempotency_registry.get_settings", webhooks.get_settings)
    monkeypatch.setattr(webhooks, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr("integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor)

    async def _no_sleep(_delay):
        return None

    monkeypatch.setattr(webhooks.asyncio, "sleep", _no_sleep)

    client = _make_client()
    response = client.post(
        "/webhooks/google-calendar",
        json={"kind": "calendar#event"},
        headers={
            "x-goog-channel-id": "channel-1",
            "x-goog-resource-id": "resource-1",
            "x-goog-resource-state": "exists",
            "x-goog-message-number": "88",
            "x-goog-channel-token": "google-token",
            "x-workspace-id": "77",
        },
    )

    assert response.status_code == 502
    assert "failed to process webhook after retries" in response.json()["detail"]
    assert len(state["audit_logs"]) == 1

    dead_letter = state["audit_logs"][0]
    assert dead_letter["workspace_id"] == 77
    assert dead_letter["action"] == "webhook.dead_letter"
    assert dead_letter["metadata"]["source"] == "google_calendar"
    assert dead_letter["metadata"]["event_id"] == "88"
    assert dead_letter["metadata"]["attempts"] == webhooks.MAX_WEBHOOK_RETRIES