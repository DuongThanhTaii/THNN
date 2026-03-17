from contextlib import contextmanager
from unittest.mock import MagicMock

from integrations.idempotency_registry import ProcessedEventRegistry


def test_build_payload_hash_is_stable_for_key_order():
    payload_a = {"b": 2, "a": 1}
    payload_b = {"a": 1, "b": 2}

    hash_a = ProcessedEventRegistry.build_payload_hash(payload_a)
    hash_b = ProcessedEventRegistry.build_payload_hash(payload_b)

    assert hash_a == hash_b


def test_register_event_returns_processed_without_database(monkeypatch):
    monkeypatch.setattr(
        "integrations.idempotency_registry.get_settings",
        lambda: type("S", (), {"database_url": ""})(),
    )

    status = ProcessedEventRegistry().register_event(
        source="jira",
        event_id="evt-1",
        payload_hash="h1",
    )

    assert status == "processed"


def test_register_event_returns_processed_on_insert(monkeypatch):
    monkeypatch.setattr(
        "integrations.idempotency_registry.get_settings",
        lambda: type("S", (), {"database_url": "postgres://demo"})(),
    )

    cursor = MagicMock()
    cursor.rowcount = 1

    @contextmanager
    def fake_get_db_cursor():
        yield cursor

    monkeypatch.setattr(
        "integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor
    )

    status = ProcessedEventRegistry().register_event(
        source="jira",
        event_id="evt-2",
        payload_hash="h2",
    )

    assert status == "processed"


def test_register_event_returns_duplicate_when_existing_hash_matches(monkeypatch):
    monkeypatch.setattr(
        "integrations.idempotency_registry.get_settings",
        lambda: type("S", (), {"database_url": "postgres://demo"})(),
    )

    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = ("same-hash",)

    @contextmanager
    def fake_get_db_cursor():
        yield cursor

    monkeypatch.setattr(
        "integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor
    )

    status = ProcessedEventRegistry().register_event(
        source="jira",
        event_id="evt-3",
        payload_hash="same-hash",
    )

    assert status == "duplicate"


def test_register_event_returns_hash_mismatch_when_existing_hash_differs(monkeypatch):
    monkeypatch.setattr(
        "integrations.idempotency_registry.get_settings",
        lambda: type("S", (), {"database_url": "postgres://demo"})(),
    )

    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = ("old-hash",)

    @contextmanager
    def fake_get_db_cursor():
        yield cursor

    monkeypatch.setattr(
        "integrations.idempotency_registry.get_db_cursor", fake_get_db_cursor
    )

    status = ProcessedEventRegistry().register_event(
        source="jira",
        event_id="evt-4",
        payload_hash="new-hash",
    )

    assert status == "hash_mismatch"
