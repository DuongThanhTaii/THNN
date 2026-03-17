"""Sync status projections for dashboard and operational visibility."""

from fastapi import APIRouter

from api.v1.schemas import SyncConflictSummary, SyncStatusProjectionResponse
from storage.db import get_db_cursor

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatusProjectionResponse)
async def get_sync_status(
    workspace_id: int, recent_limit: int = 10
) -> SyncStatusProjectionResponse:
    recent_limit = max(1, min(recent_limit, 50))

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE enabled) AS enabled
            FROM sync_policies
            WHERE workspace_id = %s
            """,
            (workspace_id,),
        )
        policy_row = cur.fetchone() or (0, 0)

        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'open') AS open_count,
                COUNT(*) FILTER (WHERE status <> 'open') AS resolved_count,
                MAX(created_at) AS last_conflict_at
            FROM sync_conflicts
            WHERE workspace_id = %s
            """,
            (workspace_id,),
        )
        conflict_row = cur.fetchone() or (0, 0, None)

        cur.execute(
            """
            SELECT id, source_system, target_system, entity_ref, reason, status, created_at, resolved_at
            FROM sync_conflicts
            WHERE workspace_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (workspace_id, recent_limit),
        )
        recent_rows = cur.fetchall()

    policies_total = int(policy_row[0] or 0)
    policies_enabled = int(policy_row[1] or 0)
    conflicts_open = int(conflict_row[0] or 0)
    conflicts_resolved = int(conflict_row[1] or 0)
    last_conflict_at = str(conflict_row[2]) if conflict_row[2] is not None else None

    if policies_enabled == 0:
        health = "idle"
    elif conflicts_open > 0:
        health = "degraded"
    else:
        health = "healthy"

    recent_conflicts = [
        SyncConflictSummary(
            id=int(row[0]),
            source_system=str(row[1]),
            target_system=str(row[2]),
            entity_ref=str(row[3]),
            reason=str(row[4]),
            status=str(row[5]),
            created_at=str(row[6]),
            resolved_at=str(row[7]) if row[7] is not None else None,
        )
        for row in recent_rows
    ]

    return SyncStatusProjectionResponse(
        workspace_id=workspace_id,
        health=health,
        policies_total=policies_total,
        policies_enabled=policies_enabled,
        conflicts_open=conflicts_open,
        conflicts_resolved=conflicts_resolved,
        last_conflict_at=last_conflict_at,
        recent_conflicts=recent_conflicts,
    )
