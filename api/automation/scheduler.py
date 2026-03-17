"""Daily automation scheduler and rule evaluation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from api.v1.realtime import publish_workspace_event
from storage.distributed_lock import try_acquire_automation_execution_lock
from storage.db import get_db_cursor

_ALLOWED_TASK_STATUSES = {"todo", "in_progress", "done", "blocked"}
_ALLOWED_TASK_PRIORITIES = {"low", "normal", "high", "urgent"}


@dataclass(slots=True)
class AutomationScheduleCandidate:
    automation_id: int
    workspace_id: int
    name: str
    action_type: str
    config: dict[str, Any]
    last_run_at: datetime | None


@dataclass(slots=True)
class _QueuedRun:
    candidate: AutomationScheduleCandidate
    scheduled_at: datetime


class AutomationActionWorker:
    """Background queue worker for automation action execution."""

    def __init__(self, queue_size: int = 500, concurrency: int = 2) -> None:
        self._queue: asyncio.Queue[_QueuedRun] = asyncio.Queue(maxsize=max(1, queue_size))
        self._concurrency = max(1, concurrency)
        self._workers: list[asyncio.Task[None]] = []
        self._stopping = False
        self._inflight: set[int] = set()

    @property
    def running(self) -> bool:
        return any(not task.done() for task in self._workers)

    async def start(self) -> None:
        if self.running:
            return
        self._stopping = False
        self._workers = [
            asyncio.create_task(self._worker_loop(i + 1))
            for i in range(self._concurrency)
        ]
        logger.info(
            "Automation action worker started "
            f"(concurrency={self._concurrency}, queue_size={self._queue.maxsize})"
        )

    async def stop(self) -> None:
        self._stopping = True
        try:
            await asyncio.wait_for(self._queue.join(), timeout=2.0)
        except TimeoutError:
            logger.warning("Automation action worker shutdown timed out with pending jobs")
        for task in self._workers:
            task.cancel()
        for task in self._workers:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        self._inflight.clear()
        # Drain queue to avoid stale references across restarts.
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        logger.info("Automation action worker stopped")

    async def enqueue(self, candidate: AutomationScheduleCandidate, now_utc: datetime) -> bool:
        automation_id = candidate.automation_id
        if automation_id in self._inflight:
            return False
        try:
            self._queue.put_nowait(_QueuedRun(candidate=candidate, scheduled_at=now_utc))
        except asyncio.QueueFull:
            logger.warning(
                "Automation action queue is full; dropping run "
                f"automation_id={automation_id}"
            )
            return False
        self._inflight.add(automation_id)
        return True

    async def _worker_loop(self, worker_id: int) -> None:
        while not self._stopping:
            queued: _QueuedRun | None = None
            try:
                queued = await self._queue.get()
                result = await asyncio.to_thread(
                    _execute_candidate,
                    queued.candidate,
                    queued.scheduled_at,
                )
                await publish_workspace_event(
                    workspace_id=queued.candidate.workspace_id,
                    event_type=(
                        "automation.run.completed"
                        if result["status"] == "success"
                        else (
                            "automation.run.skipped"
                            if result["status"] == "skipped_locked"
                            else "automation.run.failed"
                        )
                    ),
                    payload=result,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "Automation worker execution failed "
                    f"(worker={worker_id}): {type(exc).__name__}: {exc}"
                )
            finally:
                if queued is not None:
                    self._inflight.discard(queued.candidate.automation_id)
                    self._queue.task_done()


class AutomationScheduler:
    """Poll enabled automation rules and execute due daily workflows."""

    def __init__(
        self,
        poll_seconds: int = 30,
        max_batch: int = 100,
        worker_queue_size: int = 500,
        worker_concurrency: int = 2,
    ) -> None:
        self._poll_seconds = max(5, poll_seconds)
        self._max_batch = max(1, max_batch)
        self._stop_event = asyncio.Event()
        self._loop_task: asyncio.Task[None] | None = None
        self._worker = AutomationActionWorker(
            queue_size=worker_queue_size,
            concurrency=worker_concurrency,
        )

    @property
    def running(self) -> bool:
        return self._loop_task is not None and not self._loop_task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        await self._worker.start()
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info(
            "Automation scheduler started "
            f"(poll_seconds={self._poll_seconds}, max_batch={self._max_batch})"
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._loop_task is None:
            await self._worker.stop()
            return
        self._loop_task.cancel()
        try:
            await self._loop_task
        except asyncio.CancelledError:
            pass
        finally:
            self._loop_task = None
        await self._worker.stop()
        logger.info("Automation scheduler stopped")

    async def tick_once(self, now: datetime | None = None) -> int:
        now_utc = now or datetime.now(UTC)
        candidates = await asyncio.to_thread(self._fetch_candidates)
        due = [c for c in candidates if _is_daily_rule_due(c, now_utc)]

        enqueued = 0
        for candidate in due:
            if await self._worker.enqueue(candidate, now_utc):
                enqueued += 1
        return enqueued

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                executed = await self.tick_once()
                if executed:
                    logger.info(f"Automation scheduler executed {executed} run(s)")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"Automation scheduler tick failed: {type(exc).__name__}: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_seconds)
            except TimeoutError:
                continue

    def _fetch_candidates(self) -> list[AutomationScheduleCandidate]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    a.workspace_id,
                    a.name,
                    a.action_type,
                    a.config,
                    (
                        SELECT MAX(ar.created_at)
                        FROM automation_runs ar
                        WHERE ar.automation_id = a.id
                    ) AS last_run_at
                FROM automations a
                WHERE a.enabled = TRUE
                  AND a.trigger_type = 'schedule'
                ORDER BY a.updated_at DESC, a.id DESC
                LIMIT %s
                """,
                (self._max_batch,),
            )
            rows = cur.fetchall()

        candidates: list[AutomationScheduleCandidate] = []
        for row in rows:
            candidates.append(
                AutomationScheduleCandidate(
                    automation_id=int(row[0]),
                    workspace_id=int(row[1]),
                    name=str(row[2]),
                    action_type=str(row[3]),
                    config=dict(row[4] or {}),
                    last_run_at=row[5],
                )
            )
        return candidates

def _is_daily_rule_due(candidate: AutomationScheduleCandidate, now_utc: datetime) -> bool:
    schedule = _extract_daily_schedule(candidate.config)
    if schedule is None:
        return False

    hour, minute, offset_minutes, weekdays = schedule
    local_now = now_utc + timedelta(minutes=offset_minutes)

    if weekdays and local_now.weekday() not in weekdays:
        return False

    scheduled_local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local_now < scheduled_local:
        return False

    if candidate.last_run_at is None:
        return True

    last_run = candidate.last_run_at
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=UTC)

    local_last_run = last_run.astimezone(UTC) + timedelta(minutes=offset_minutes)
    return local_last_run.date() < local_now.date()


def _extract_daily_schedule(
    config: dict[str, Any],
) -> tuple[int, int, int, set[int]] | None:
    hour: int | None = None
    minute = 0

    daily_at = config.get("daily_at")
    if isinstance(daily_at, str) and ":" in daily_at:
        parts = daily_at.split(":", maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            hour = int(parts[0])
            minute = int(parts[1])

    if hour is None and isinstance(config.get("hour"), int):
        hour = int(config["hour"])
    if isinstance(config.get("minute"), int):
        minute = int(config["minute"])

    if hour is None or not (0 <= hour <= 23) or not (0 <= minute <= 59):
        return None

    offset_minutes_raw = config.get("timezone_offset_minutes", 0)
    offset_minutes = int(offset_minutes_raw) if isinstance(offset_minutes_raw, int) else 0

    weekdays_raw = config.get("weekdays")
    weekdays: set[int] = set()
    if isinstance(weekdays_raw, list):
        for value in weekdays_raw:
            if isinstance(value, int) and 0 <= value <= 6:
                weekdays.add(value)

    return hour, minute, offset_minutes, weekdays


def _apply_automation_action(cur, candidate: AutomationScheduleCandidate) -> int | None:
    action = candidate.action_type.strip().lower()

    if action == "create_task":
        return _create_task_from_template(cur, candidate)

    if action == "update_task_status":
        task_id = _get_configured_task_id(candidate.config)
        if task_id is None:
            raise ValueError("config.task_id is required for update_task_status")
        status = candidate.config.get("set_task_status")
        if not isinstance(status, str) or status not in _ALLOWED_TASK_STATUSES:
            raise ValueError("config.set_task_status is invalid")

        cur.execute(
            """
            UPDATE tasks
            SET status = %s,
                updated_at = NOW()
            WHERE id = %s AND workspace_id = %s
            RETURNING id
            """,
            (status, task_id, candidate.workspace_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("configured task_id not found in workspace")
        return int(row[0])

    # Unknown action types still produce an automation_run for visibility.
    return _get_configured_task_id(candidate.config)


def _create_task_from_template(cur, candidate: AutomationScheduleCandidate) -> int:
    template = candidate.config.get("task_template")
    if not isinstance(template, dict):
        template = {}

    title = template.get("title")
    if not isinstance(title, str) or not title.strip():
        title = f"[Automation] {candidate.name}"

    description = template.get("description")
    if description is not None and not isinstance(description, str):
        description = str(description)

    priority = template.get("priority", "normal")
    if not isinstance(priority, str) or priority not in _ALLOWED_TASK_PRIORITIES:
        priority = "normal"

    cur.execute(
        """
        INSERT INTO tasks(workspace_id, title, description, status, priority, source)
        VALUES (%s, %s, %s, 'todo', %s, 'automation')
        RETURNING id
        """,
        (candidate.workspace_id, title.strip(), description, priority),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("failed to create task for automation")
    return int(row[0])


def _get_configured_task_id(config: dict[str, Any]) -> int | None:
    task_id = config.get("task_id")
    if isinstance(task_id, int) and task_id > 0:
        return task_id
    return None


def _create_task_run(
    cur,
    task_id: int,
    workspace_id: int,
    trigger_source: str,
    metadata: dict[str, Any],
) -> int:
    cur.execute(
        """
        INSERT INTO task_runs(
            task_id,
            workspace_id,
            trigger_source,
            status,
            started_at,
            finished_at,
            metadata
        )
        VALUES (%s, %s, %s, 'success', NOW(), NOW(), %s)
        RETURNING id
        """,
        (task_id, workspace_id, trigger_source, metadata),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("failed to create task run")
    return int(row[0])


def _execute_candidate(
    candidate: AutomationScheduleCandidate,
    now_utc: datetime,
) -> dict[str, Any]:
    with get_db_cursor() as cur:
        if not try_acquire_automation_execution_lock(
            cur,
            workspace_id=candidate.workspace_id,
            automation_id=candidate.automation_id,
        ):
            return {
                "automation_id": candidate.automation_id,
                "workspace_id": candidate.workspace_id,
                "status": "skipped_locked",
                "reason": "distributed lock unavailable",
            }

        cur.execute(
            """
            INSERT INTO automation_runs(
                automation_id,
                workspace_id,
                status,
                started_at,
                metadata
            )
            VALUES (%s, %s, 'running', NOW(), %s)
            RETURNING id
            """,
            (
                candidate.automation_id,
                candidate.workspace_id,
                {
                    "trigger_source": "scheduler",
                    "evaluated_at": now_utc.isoformat(),
                    "action_type": candidate.action_type,
                },
            ),
        )
        run_row = cur.fetchone()
        if run_row is None:
            raise RuntimeError("failed to create automation run")
        automation_run_id = int(run_row[0])

        task_id: int | None = None
        task_run_id: int | None = None
        try:
            task_id = _apply_automation_action(cur, candidate)
            if task_id is not None:
                task_run_id = _create_task_run(
                    cur=cur,
                    task_id=task_id,
                    workspace_id=candidate.workspace_id,
                    trigger_source="automation_schedule",
                    metadata={
                        "automation_id": candidate.automation_id,
                        "automation_run_id": automation_run_id,
                    },
                )

            cur.execute(
                """
                UPDATE automation_runs
                SET status = 'success',
                    finished_at = NOW(),
                    task_id = %s,
                    task_run_id = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (task_id, task_run_id, automation_run_id),
            )
            return {
                "automation_id": candidate.automation_id,
                "workspace_id": candidate.workspace_id,
                "automation_run_id": automation_run_id,
                "task_id": task_id,
                "task_run_id": task_run_id,
                "status": "success",
            }
        except Exception as exc:
            cur.execute(
                """
                UPDATE automation_runs
                SET status = 'failed',
                    finished_at = NOW(),
                    error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (str(exc), automation_run_id),
            )
            return {
                "automation_id": candidate.automation_id,
                "workspace_id": candidate.workspace_id,
                "automation_run_id": automation_run_id,
                "status": "failed",
                "error": str(exc),
            }
