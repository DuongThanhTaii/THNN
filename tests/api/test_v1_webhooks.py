import hashlib
import hmac
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routers import webhooks


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(webhooks.router)
    return TestClient(app)


def _settings(
    *, jira_secret: str = "", google_secret: str = "", database_url: str = ""
):
    return SimpleNamespace(
        jira_webhook_secret=jira_secret,
        google_webhook_secret=google_secret,
        database_url=database_url,
    )


def test_jira_webhook_accepts_legacy_secret(monkeypatch):
    monkeypatch.setattr(webhooks, "get_settings", lambda: _settings(jira_secret="abc"))
    monkeypatch.setattr(webhooks, "_record_processed_event", lambda _event: True)

    client = _make_client()
    response = client.post(
        "/webhooks/jira",
        json={"timestamp": 1, "webhookEvent": "jira:issue_updated"},
        headers={"x-hook-secret": "abc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["normalized"]["source"] == "jira"
    assert payload["processing"]["status"] == "processed"


def test_jira_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(
        webhooks, "get_settings", lambda: _settings(jira_secret="jira-secret")
    )

    client = _make_client()
    response = client.post(
        "/webhooks/jira",
        json={"timestamp": 1, "webhookEvent": "jira:issue_updated"},
        headers={"x-atlassian-webhook-signature": "sha256=bad"},
    )

    assert response.status_code == 401


def test_jira_webhook_accepts_hmac_signature(monkeypatch):
    monkeypatch.setattr(
        webhooks, "get_settings", lambda: _settings(jira_secret="jira-secret")
    )

    body = b'{"timestamp":1,"webhookEvent":"jira:issue_updated"}'
    digest = hmac.new(b"jira-secret", body, hashlib.sha256).hexdigest()

    client = _make_client()
    response = client.post(
        "/webhooks/jira",
        content=body,
        headers={
            "content-type": "application/json",
            "x-atlassian-webhook-signature": f"sha256={digest}",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["internal_event"]["id"].startswith("jira:")


def test_jira_webhook_retry_then_success(monkeypatch):
    monkeypatch.setattr(webhooks, "get_settings", lambda: _settings(jira_secret="abc"))

    attempts = {"count": 0}

    def flaky_record(_event):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary")
        return True

    async def fast_sleep(_delay):
        return None

    monkeypatch.setattr(webhooks, "_record_processed_event", flaky_record)
    monkeypatch.setattr(webhooks.asyncio, "sleep", fast_sleep)

    client = _make_client()
    response = client.post(
        "/webhooks/jira",
        json={"timestamp": 1, "webhookEvent": "jira:issue_updated"},
        headers={"x-hook-secret": "abc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processing"]["attempts"] == 3
    assert payload["processing"]["status"] == "processed"


def test_jira_webhook_dead_letter_after_max_retries(monkeypatch):
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(jira_secret="abc", database_url="postgres://demo"),
    )

    def always_fail(_event):
        raise RuntimeError("boom")

    dead_letter_calls = []

    def capture_dead_letter(*, source, event, error, attempts):
        dead_letter_calls.append(
            {
                "source": source,
                "event_id": event["event_id"],
                "error": error,
                "attempts": attempts,
            }
        )

    async def fast_sleep(_delay):
        return None

    monkeypatch.setattr(webhooks, "_record_processed_event", always_fail)
    monkeypatch.setattr(webhooks, "_record_dead_letter", capture_dead_letter)
    monkeypatch.setattr(webhooks.asyncio, "sleep", fast_sleep)

    client = _make_client()
    response = client.post(
        "/webhooks/jira",
        json={"timestamp": 1, "webhookEvent": "jira:issue_updated"},
        headers={"x-hook-secret": "abc"},
    )

    assert response.status_code == 502
    assert len(dead_letter_calls) == 1
    assert dead_letter_calls[0]["source"] == "jira"
    assert dead_letter_calls[0]["attempts"] == webhooks.MAX_WEBHOOK_RETRIES


def test_google_webhook_rejects_bad_token(monkeypatch):
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(google_secret="good-token"),
    )

    client = _make_client()
    response = client.post(
        "/webhooks/google-calendar",
        json={},
        headers={
            "x-goog-channel-id": "cid",
            "x-goog-resource-id": "rid",
            "x-goog-resource-state": "exists",
            "x-goog-message-number": "1",
            "x-goog-channel-token": "bad-token",
        },
    )

    assert response.status_code == 401


def test_google_webhook_accepts_valid_headers_and_normalizes(monkeypatch):
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(google_secret="good-token"),
    )

    client = _make_client()
    response = client.post(
        "/webhooks/google-calendar",
        json={"kind": "calendar#event"},
        headers={
            "x-goog-channel-id": "cid",
            "x-goog-resource-id": "rid",
            "x-goog-resource-state": "exists",
            "x-goog-message-number": "42",
            "x-goog-channel-token": "good-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["normalized"]["source"] == "google_calendar"
    assert payload["internal_event"]["event_id"] == "42"


def test_google_webhook_marks_duplicates(monkeypatch):
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: _settings(google_secret="good-token"),
    )
    monkeypatch.setattr(webhooks, "_record_processed_event", lambda _event: False)

    client = _make_client()
    response = client.post(
        "/webhooks/google-calendar",
        json={"kind": "calendar#event"},
        headers={
            "x-goog-channel-id": "cid",
            "x-goog-resource-id": "rid",
            "x-goog-resource-state": "exists",
            "x-goog-message-number": "10",
            "x-goog-channel-token": "good-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["processing"]["status"] == "duplicate"
