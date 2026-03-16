"""Workspace and user management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.v1.realtime import publish_workspace_event
from storage.db import get_db_cursor

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreateRequest(BaseModel):
    slug: str = Field(min_length=3, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    owner_email: str = Field(min_length=3, max_length=255)
    owner_display_name: str = Field(min_length=1, max_length=200)


class WorkspaceResponse(BaseModel):
    id: int
    slug: str
    name: str
    owner_user_id: int | None


class WorkspaceUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=3, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    owner_user_id: int | None = Field(default=None, ge=1)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(limit: int = 100, offset: int = 0) -> list[WorkspaceResponse]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, slug, name, owner_user_id
            FROM workspaces
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()

    return [
        WorkspaceResponse(
            id=int(row[0]),
            slug=str(row[1]),
            name=str(row[2]),
            owner_user_id=int(row[3]) if row[3] is not None else None,
        )
        for row in rows
    ]


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(body: WorkspaceCreateRequest) -> WorkspaceResponse:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO users(email, display_name)
            VALUES (%s, %s)
            ON CONFLICT (email)
            DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = NOW()
            RETURNING id
            """,
            (body.owner_email.strip().lower(), body.owner_display_name.strip()),
        )
        owner_user_id = int(cur.fetchone()[0])

        cur.execute(
            """
            INSERT INTO workspaces(slug, name, owner_user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug)
            DO UPDATE SET name = EXCLUDED.name, owner_user_id = EXCLUDED.owner_user_id, updated_at = NOW()
            RETURNING id, slug, name, owner_user_id
            """,
            (body.slug.strip().lower(), body.name.strip(), owner_user_id),
        )
        row = cur.fetchone()

    workspace = WorkspaceResponse(
        id=int(row[0]),
        slug=str(row[1]),
        name=str(row[2]),
        owner_user_id=int(row[3]) if row[3] is not None else None,
    )
    await publish_workspace_event(
        workspace_id=workspace.id,
        event_type="workspace.created",
        payload=workspace.model_dump(),
    )
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: int) -> WorkspaceResponse:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, slug, name, owner_user_id
            FROM workspaces
            WHERE id = %s
            """,
            (workspace_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="workspace not found")

    return WorkspaceResponse(
        id=int(row[0]),
        slug=str(row[1]),
        name=str(row[2]),
        owner_user_id=int(row[3]) if row[3] is not None else None,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: int,
    body: WorkspaceUpdateRequest,
) -> WorkspaceResponse:
    updates: list[str] = []
    values: list[object] = []

    if body.slug is not None:
        updates.append("slug = %s")
        values.append(body.slug.strip().lower())
    if body.name is not None:
        updates.append("name = %s")
        values.append(body.name.strip())
    if body.owner_user_id is not None:
        updates.append("owner_user_id = %s")
        values.append(body.owner_user_id)

    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    updates.append("updated_at = NOW()")
    set_sql = ", ".join(updates)

    with get_db_cursor() as cur:
        cur.execute(
            f"""
            UPDATE workspaces
            SET {set_sql}
            WHERE id = %s
            RETURNING id, slug, name, owner_user_id
            """,
            [*values, workspace_id],
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="workspace not found")

    workspace = WorkspaceResponse(
        id=int(row[0]),
        slug=str(row[1]),
        name=str(row[2]),
        owner_user_id=int(row[3]) if row[3] is not None else None,
    )
    await publish_workspace_event(
        workspace_id=workspace.id,
        event_type="workspace.updated",
        payload=workspace.model_dump(),
    )
    return workspace


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: int) -> dict:
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM workspaces WHERE id = %s", (workspace_id,))
        deleted = cur.rowcount

    if deleted == 0:
        raise HTTPException(status_code=404, detail="workspace not found")

    await publish_workspace_event(
        workspace_id=workspace_id,
        event_type="workspace.deleted",
        payload={"workspace_id": workspace_id},
    )

    return {"status": "ok", "deleted": deleted}
