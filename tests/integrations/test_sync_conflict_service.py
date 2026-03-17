from contextlib import contextmanager
from unittest.mock import MagicMock

from integrations.sync_conflicts import SyncConflictService


def test_manual_policy_detects_open_conflict_and_keeps_target_value():
    service = SyncConflictService()

    result = service.detect_and_resolve(
        workspace_id=1,
        source_system="jira",
        target_system="google_calendar",
        entity_ref="OPS-17",
        source_fields={"status": "In Progress", "summary": "Deploy"},
        target_fields={"status": "Done", "summary": "Deploy"},
        policy="manual",
        persist_conflicts=False,
    )

    assert result["resolved_fields"]["status"] == "Done"
    assert result["resolved_fields"]["summary"] == "Deploy"
    assert result["has_unresolved_conflicts"] is True
    assert result["conflicts"] == [
        {
            "field": "status",
            "source_value": "In Progress",
            "target_value": "Done",
            "status": "open",
            "selected_value": "Done",
        }
    ]


def test_last_write_wins_uses_latest_timestamp():
    service = SyncConflictService()

    result = service.detect_and_resolve(
        workspace_id=1,
        source_system="jira",
        target_system="google_calendar",
        entity_ref="OPS-18",
        source_fields={"summary": "Updated from Jira"},
        target_fields={"summary": "Updated from Calendar"},
        policy="last_write_wins",
        source_updated_at="2026-03-16T09:00:00Z",
        target_updated_at="2026-03-16T08:00:00Z",
        persist_conflicts=False,
    )

    assert result["resolved_fields"]["summary"] == "Updated from Jira"
    assert result["has_unresolved_conflicts"] is False
    assert result["conflicts"][0]["status"] == "resolved"


def test_source_of_truth_uses_field_owner_map():
    service = SyncConflictService()

    result = service.detect_and_resolve(
        workspace_id=1,
        source_system="jira",
        target_system="google_calendar",
        entity_ref="OPS-19",
        source_fields={"status": "In Progress", "timeslot": "A"},
        target_fields={"status": "Done", "timeslot": "B"},
        policy="source_of_truth",
        field_owners={"status": "source", "timeslot": "target"},
        persist_conflicts=False,
    )

    assert result["resolved_fields"]["status"] == "In Progress"
    assert result["resolved_fields"]["timeslot"] == "B"
    assert result["has_unresolved_conflicts"] is False


def test_manual_policy_persists_open_conflicts_when_db_available(monkeypatch):
    service = SyncConflictService()
    monkeypatch.setattr(
        "integrations.sync_conflicts.get_settings",
        lambda: type("S", (), {"database_url": "postgres://demo"})(),
    )

    cursor = MagicMock()

    @contextmanager
    def fake_get_db_cursor():
        yield cursor

    monkeypatch.setattr("integrations.sync_conflicts.get_db_cursor", fake_get_db_cursor)

    result = service.detect_and_resolve(
        workspace_id=42,
        source_system="jira",
        target_system="google_calendar",
        entity_ref="OPS-20",
        source_fields={"status": "In Progress"},
        target_fields={"status": "Done"},
        policy="manual",
        persist_conflicts=True,
    )

    assert result["has_unresolved_conflicts"] is True
    assert cursor.execute.call_count == 1
    sql = cursor.execute.call_args.args[0]
    params = cursor.execute.call_args.args[1]
    assert "INSERT INTO sync_conflicts" in sql
    assert params[0] == 42
    assert params[1] == "jira"
    assert params[2] == "google_calendar"
    assert params[3] == "OPS-20"
