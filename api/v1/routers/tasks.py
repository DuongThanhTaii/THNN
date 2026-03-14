"""Task endpoints (initial CRUD scaffold)."""

from fastapi import APIRouter, HTTPException

from api.v1.schemas import TaskCreateRequest, TaskResponse
from storage.db import get_db_cursor

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(workspace_id: int) -> list[TaskResponse]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, workspace_id, title, description, status, priority
            FROM tasks
            WHERE workspace_id = %s
            ORDER BY id DESC
            LIMIT 200
            """,
            (workspace_id,),
        )
        rows = cur.fetchall()

    return [
        TaskResponse(
            id=row[0],
            workspace_id=row[1],
            title=row[2],
            description=row[3],
            status=row[4],
            priority=row[5],
        )
        for row in rows
    ]


@router.post("", response_model=TaskResponse)
async def create_task(body: TaskCreateRequest) -> TaskResponse:
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
    return TaskResponse(
        id=row[0],
        workspace_id=row[1],
        title=row[2],
        description=row[3],
        status=row[4],
        priority=row[5],
    )
