import asyncio
import json
import threading
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.v1.routers import webhooks


def _settings(*, jira_secret: str = "", google_secret: str = "", database_url: str = ""):
    return SimpleNamespace(
        jira_webhook_secret=jira_secret,
        google_webhook_secret=google_secret,
        database_url=database_url,
    )


def _build_async_client() -> AsyncClient:
    app = FastAPI()
    app.include_router(webhooks.router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class _StatefulWebhookCursor:
    def __init__(self, state: dict):
        self._state = state
        self.rowcount = 0
        self._fetchone_result = None

    def execute(self, sql, params=None):
        query = " ".join(str(sql).lower().split())
        params = params or ()

        if "insert into processed_events" in query:
            with self._state["lock"]:
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
            with self._state["lock"]:
                existing = self._state["processed_events"].get(key)
            self._fetchone_result = (existing,) if existing else None
            return

        if "insert into audit_logs" in query:
            with self._state["lock"]:
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

        raise AssertionError(f"Unexpected SQL in webhook burst load test: {sql}")

    def fetchone(self):
        return self._fetchone_result


def _make_fake_db(*, fail_processed_event: bool = False):
    state = {
        "processed_events": {},
        "audit_logs": [],
        "fail_processed_event": fail_processed_event,
        "lock": threading.Lock(),
    }

    @contextmanager
    def _fake_get_db_cursor():
        yield _StatefulWebhookCursor(state)

    return state, _fake_get_db_cursor


@pytest.mark.asyncio
async def test_burst_jira_webhooks_unique_events_all_processed(monkeypatch):
    state, fake_get_db_cursor = _make_fake_db()
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(jira_secret="jira-secret", database_url="postgres://demo"),
    )
    monkeypatch.setattr("integrations.idempotency_registry.get_settings", webhooks.get_settings)
    monkeypatch.setattr(webhooks, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr("integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor)

    async with _build_async_client() as client:
        requests = [
            client.post(
                "/webhooks/jira",
                json={"timestamp": 1800000000 + i, "webhookEvent": "jira:issue_updated"},
                headers={"x-hook-secret": "jira-secret"},
            )
            for i in range(60)
        ]
        responses = await asyncio.gather(*requests)

    payloads = [r.json() for r in responses]
    assert all(r.status_code == 200 for r in responses)
    assert all(p["processing"]["status"] == "processed" for p in payloads)
    assert len(state["processed_events"]) == 60
    assert state["audit_logs"] == []


@pytest.mark.asyncio
async def test_burst_google_webhooks_duplicate_event_majority_marked_duplicate(monkeypatch):
    state, fake_get_db_cursor = _make_fake_db()
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(google_secret="google-token", database_url="postgres://demo"),
    )
    monkeypatch.setattr("integrations.idempotency_registry.get_settings", webhooks.get_settings)
    monkeypatch.setattr(webhooks, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr("integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor)

    headers = {
        "x-goog-channel-id": "channel-1",
        "x-goog-resource-id": "resource-1",
        "x-goog-resource-state": "exists",
        "x-goog-message-number": "999",
        "x-goog-channel-token": "google-token",
    }

    async with _build_async_client() as client:
        requests = [
            client.post(
                "/webhooks/google-calendar",
                json={"kind": "calendar#event", "sequence": i},
                headers=headers,
            )
            for i in range(80)
        ]
        responses = await asyncio.gather(*requests)

    payloads = [r.json() for r in responses]
    processed_count = sum(1 for p in payloads if p["processing"]["status"] == "processed")
    duplicate_count = sum(1 for p in payloads if p["processing"]["status"] == "duplicate")

    assert all(r.status_code == 200 for r in responses)
    assert processed_count == 1
    assert duplicate_count == 79
    assert len(state["processed_events"]) == 1
    assert state["audit_logs"] == []


@pytest.mark.asyncio
async def test_burst_jira_webhooks_db_failures_create_dead_letters(monkeypatch):
    state, fake_get_db_cursor = _make_fake_db(fail_processed_event=True)
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(jira_secret="jira-secret", database_url="postgres://demo"),
    )
    monkeypatch.setattr("integrations.idempotency_registry.get_settings", webhooks.get_settings)
    monkeypatch.setattr(webhooks, "get_db_cursor", fake_get_db_cursor)
    monkeypatch.setattr("integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor)

    async def _no_sleep(_delay):
        return None

    monkeypatch.setattr(webhooks.asyncio, "sleep", _no_sleep)

    async with _build_async_client() as client:
        requests = [
            client.post(
                "/webhooks/jira",
                json={"timestamp": 1900000000 + i, "webhookEvent": "jira:issue_updated"},
                headers={"x-hook-secret": "jira-secret", "x-workspace-id": "44"},
            )
            for i in range(25)
        ]
        responses = await asyncio.gather(*requests)

    assert all(r.status_code == 502 for r in responses)
    assert len(state["audit_logs"]) == 25
    assert all(log["action"] == "webhook.dead_letter" for log in state["audit_logs"])
    assert all(log["workspace_id"] == 44 for log in state["audit_logs"])
