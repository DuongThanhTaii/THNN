"""Automation CRUD endpoints."""

from fastapi import APIRouter, HTTPException

from api.v1.schemas import (
    AutomationCreateRequest,
    AutomationResponse,
    AutomationUpdateRequest,
)
from storage.db import get_db_cursor

router = APIRouter(prefix="/automations", tags=["automations"])


def _automation_from_row(row) -> AutomationResponse:
    return AutomationResponse(
        id=int(row[0]),
        workspace_id=int(row[1]),
        name=str(row[2]),
        trigger_type=str(row[3]),
        action_type=str(row[4]),
        config=dict(row[5] or {}),
        enabled=bool(row[6]),
    )


@router.get("", response_model=list[AutomationResponse])
async def list_automations(
    workspace_id: int,
    enabled: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AutomationResponse]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    where_parts = ["workspace_id = %s"]
    params: list[object] = [workspace_id]

    if enabled is not None:
        where_parts.append("enabled = %s")
        params.append(enabled)

    where_sql = " AND ".join(where_parts)

    with get_db_cursor() as cur:
        cur.execute(
            f"""
            SELECT id, workspace_id, name, trigger_type, action_type, config, enabled
            FROM automations
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        )
        rows = cur.fetchall()

    return [_automation_from_row(row) for row in rows]


@router.post("", response_model=AutomationResponse)
async def create_automation(body: AutomationCreateRequest) -> AutomationResponse:
    with get_db_cursor() as cur:
        cur.execute("SELECT id FROM workspaces WHERE id = %s", (body.workspace_id,))
        workspace = cur.fetchone()
        if workspace is None:
            raise HTTPException(status_code=404, detail="workspace not found")

        cur.execute(
            """
            INSERT INTO automations(workspace_id, name, trigger_type, action_type, config, enabled)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, workspace_id, name, trigger_type, action_type, config, enabled
            """,
            (
                body.workspace_id,
                body.name.strip(),
                body.trigger_type.strip(),
                body.action_type.strip(),
                body.config,
                body.enabled,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="failed to create automation")
    return _automation_from_row(row)


@router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: int,
    body: AutomationUpdateRequest,
) -> AutomationResponse:
    updates: list[str] = []
    values: list[object] = []

    if body.name is not None:
        updates.append("name = %s")
        values.append(body.name.strip())
    if body.trigger_type is not None:
        updates.append("trigger_type = %s")
        values.append(body.trigger_type.strip())
    if body.action_type is not None:
        updates.append("action_type = %s")
        values.append(body.action_type.strip())
    if body.config is not None:
        updates.append("config = %s")
        values.append(body.config)
    if body.enabled is not None:
        updates.append("enabled = %s")
        values.append(body.enabled)

    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    updates.append("updated_at = NOW()")
    set_sql = ", ".join(updates)

    with get_db_cursor() as cur:
        cur.execute(
            f"""
            UPDATE automations
            SET {set_sql}
            WHERE id = %s AND workspace_id = %s
            RETURNING id, workspace_id, name, trigger_type, action_type, config, enabled
            """,
            [*values, automation_id, body.workspace_id],
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="automation not found")
    return _automation_from_row(row)


@router.delete("/{automation_id}")
async def delete_automation(
    automation_id: int, workspace_id: int
) -> dict[str, int | str]:
    with get_db_cursor() as cur:
        cur.execute(
            "DELETE FROM automations WHERE id = %s AND workspace_id = %s",
            (automation_id, workspace_id),
        )
        deleted = cur.rowcount

    if deleted == 0:
        raise HTTPException(status_code=404, detail="automation not found")

    return {"status": "ok", "deleted": deleted}
