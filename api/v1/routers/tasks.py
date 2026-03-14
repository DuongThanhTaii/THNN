"""Task endpoints (initial CRUD scaffold)."""

from fastapi import APIRouter, HTTPException

from api.v1.schemas import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from storage.db import get_db_cursor

router = APIRouter(prefix="/tasks", tags=["tasks"])

ALLOWED_STATUSES = {"todo", "in_progress", "done", "blocked"}
ALLOWED_PRIORITIES = {"low", "normal", "high", "urgent"}


def _task_from_row(row) -> TaskResponse:
    return TaskResponse(
        id=row[0],
        workspace_id=row[1],
        title=row[2],
        description=row[3],
        status=row[4],
        priority=row[5],
    )


def _validate_status_priority(status: str | None, priority: str | None) -> None:
    if status is not None and status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail=f"invalid status: {status}")
    if priority is not None and priority not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"invalid priority: {priority}")


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    workspace_id: int,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TaskResponse]:
    _validate_status_priority(status, None)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    where_parts = ["workspace_id = %s"]
    params: list[object] = [workspace_id]

    if status:
        where_parts.append("status = %s")
        params.append(status)

    if q and q.strip():
        where_parts.append("(title ILIKE %s OR COALESCE(description, '') ILIKE %s)")
        query = f"%{q.strip()}%"
        params.extend([query, query])

    where_sql = " AND ".join(where_parts)

    with get_db_cursor() as cur:
        cur.execute(
            f"""
            SELECT id, workspace_id, title, description, status, priority
            FROM tasks
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        )
        rows = cur.fetchall()

    return [_task_from_row(row) for row in rows]


@router.post("", response_model=TaskResponse)
async def create_task(body: TaskCreateRequest) -> TaskResponse:
    _validate_status_priority("todo", "normal")
    with get_db_cursor() as cur:
        cur.execute("SELECT id FROM workspaces WHERE id = %s", (body.workspace_id,))
        ws = cur.fetchone()
        if ws is None:
            raise HTTPException(status_code=404, detail="workspace not found")

        cur.execute(
            """
            INSERT INTO tasks(workspace_id, title, description, status, priority)
            VALUES (%s, %s, %s, 'todo', 'normal')
            RETURNING id, workspace_id, title, description, status, priority
            """,
            (body.workspace_id, body.title, body.description),
        )
        row = cur.fetchone()

    assert row is not None
    return _task_from_row(row)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, body: TaskUpdateRequest) -> TaskResponse:
    _validate_status_priority(body.status, body.priority)

    updates: list[str] = []
    values: list[object] = []

    if body.title is not None:
        updates.append("title = %s")
        values.append(body.title.strip())
    if body.description is not None:
        updates.append("description = %s")
        values.append(body.description)
    if body.status is not None:
        updates.append("status = %s")
        values.append(body.status)
    if body.priority is not None:
        updates.append("priority = %s")
        values.append(body.priority)

    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    updates.append("updated_at = NOW()")
    set_sql = ", ".join(updates)

    with get_db_cursor() as cur:
        cur.execute(
            f"""
            UPDATE tasks
            SET {set_sql}
            WHERE id = %s AND workspace_id = %s
            RETURNING id, workspace_id, title, description, status, priority
            """,
            [*values, task_id, body.workspace_id],
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _task_from_row(row)


@router.delete("/{task_id}")
async def delete_task(task_id: int, workspace_id: int) -> dict:
    with get_db_cursor() as cur:
        cur.execute(
            "DELETE FROM tasks WHERE id = %s AND workspace_id = %s",
            (task_id, workspace_id),
        )
        deleted = cur.rowcount

    if deleted == 0:
        raise HTTPException(status_code=404, detail="task not found")
    return {"status": "ok", "deleted": deleted}
