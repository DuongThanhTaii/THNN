import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from api.automation import scheduler
from api.automation.scheduler import AutomationScheduleCandidate, AutomationScheduler


def test_extract_daily_schedule_parses_daily_at_and_weekdays():
    parsed = scheduler._extract_daily_schedule(
        {
            "daily_at": "09:30",
            "timezone_offset_minutes": 420,
            "weekdays": [0, 2, 4, 8],
        }
    )

    assert parsed is not None
    hour, minute, offset, weekdays = parsed
    assert hour == 9
    assert minute == 30
    assert offset == 420
    assert weekdays == {0, 2, 4}


def test_is_daily_rule_due_true_when_past_schedule_and_not_ran_today():
    candidate = AutomationScheduleCandidate(
        automation_id=10,
        workspace_id=1,
        name="Daily sync",
        action_type="create_task",
        config={"daily_at": "09:00"},
        last_run_at=datetime(2026, 3, 16, 10, 0, tzinfo=UTC),
    )

    now_utc = datetime(2026, 3, 17, 9, 5, tzinfo=UTC)
    assert scheduler._is_daily_rule_due(candidate, now_utc) is True


def test_is_daily_rule_due_false_when_already_ran_today():
    candidate = AutomationScheduleCandidate(
        automation_id=11,
        workspace_id=1,
        name="Daily sync",
        action_type="create_task",
        config={"daily_at": "09:00"},
        last_run_at=datetime(2026, 3, 17, 9, 1, tzinfo=UTC),
    )

    now_utc = datetime(2026, 3, 17, 9, 30, tzinfo=UTC)
    assert scheduler._is_daily_rule_due(candidate, now_utc) is False


@pytest.mark.asyncio
async def test_tick_once_executes_only_due_candidate(monkeypatch):
    due = AutomationScheduleCandidate(
        automation_id=1,
        workspace_id=1,
        name="A",
        action_type="create_task",
        config={"daily_at": "08:00"},
        last_run_at=None,
    )
    not_due = AutomationScheduleCandidate(
        automation_id=2,
        workspace_id=1,
        name="B",
        action_type="create_task",
        config={"daily_at": "23:59"},
        last_run_at=None,
    )

    s = AutomationScheduler(poll_seconds=30, max_batch=10)
    monkeypatch.setattr(s, "_fetch_candidates", lambda: [due, not_due])

    enqueue_calls: list[int] = []

    async def _fake_enqueue(candidate, _now):
        enqueue_calls.append(candidate.automation_id)
        return True

    monkeypatch.setattr(s._worker, "enqueue", _fake_enqueue)

    executed_count = await s.tick_once(now=datetime(2026, 3, 17, 10, 0, tzinfo=UTC))

    assert executed_count == 1
    assert enqueue_calls == [1]


@pytest.mark.asyncio
async def test_worker_enqueue_skips_duplicate_inflight_candidate():
    candidate = AutomationScheduleCandidate(
        automation_id=21,
        workspace_id=1,
        name="Queue once",
        action_type="create_task",
        config={"daily_at": "08:00"},
        last_run_at=None,
    )
    now_utc = datetime(2026, 3, 17, 10, 0, tzinfo=UTC)

    worker = scheduler.AutomationActionWorker(queue_size=10, concurrency=1)
    first = await worker.enqueue(candidate, now_utc)
    second = await worker.enqueue(candidate, now_utc)

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_worker_loop_processes_job_and_publishes_event(monkeypatch):
    candidate = AutomationScheduleCandidate(
        automation_id=22,
        workspace_id=7,
        name="Queue run",
        action_type="create_task",
        config={"daily_at": "08:00"},
        last_run_at=None,
    )
    now_utc = datetime(2026, 3, 17, 11, 0, tzinfo=UTC)

    def _fake_execute(_candidate, _scheduled_at):
        return {
            "automation_id": 22,
            "workspace_id": 7,
            "automation_run_id": 501,
            "status": "success",
        }

    monkeypatch.setattr(scheduler, "_execute_candidate", _fake_execute)

    published: list[str] = []

    async def _fake_publish(workspace_id: int, event_type: str, payload):
        assert workspace_id == 7
        assert payload["automation_run_id"] == 501
        published.append(event_type)

    monkeypatch.setattr(scheduler, "publish_workspace_event", _fake_publish)

    worker = scheduler.AutomationActionWorker(queue_size=10, concurrency=1)
    await worker.start()
    queued = await worker.enqueue(candidate, now_utc)
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    await worker.stop()

    assert queued is True
    assert published == ["automation.run.completed"]


def test_apply_automation_action_updates_task_status():
    candidate = AutomationScheduleCandidate(
        automation_id=7,
        workspace_id=2,
        name="Status update",
        action_type="update_task_status",
        config={"task_id": 44, "set_task_status": "done"},
        last_run_at=None,
    )

    cur = MagicMock()
    cur.fetchone.return_value = (44,)

    task_id = scheduler._apply_automation_action(cur, candidate)

    assert task_id == 44
    cur.execute.assert_called_once()
