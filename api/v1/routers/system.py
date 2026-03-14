"""System endpoints for API v1."""

from fastapi import APIRouter

from api.v1.schemas import BootstrapResponse, HealthResponse
from config.settings import get_settings
from storage.db import can_connect, get_db_cursor

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=HealthResponse)
async def status() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        db_connected=can_connect() if settings.database_url.strip() else False,
        provider=settings.provider_type,
        environment=settings.app_env,
    )


@router.post("/bootstrap-demo", response_model=BootstrapResponse)
async def bootstrap_demo() -> BootstrapResponse:
    """Create a default user/workspace if they don't exist.

    This endpoint is intended for quick local bootstrap so frontend tasks can
    start creating records immediately.
    """
    default_email = "demo@local.agent"
    default_name = "Demo Owner"
    default_slug = "demo-workspace"
    default_workspace_name = "Demo Workspace"

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO app_users(email, display_name)
            VALUES (%s, %s)
            ON CONFLICT (email)
            DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = NOW()
            RETURNING id
            """,
            (default_email, default_name),
        )
        user_id = int(cur.fetchone()[0])

        cur.execute(
            """
            INSERT INTO workspaces(slug, name, owner_user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug)
            DO UPDATE SET name = EXCLUDED.name, owner_user_id = EXCLUDED.owner_user_id, updated_at = NOW()
            RETURNING id, slug, name
            """,
            (default_slug, default_workspace_name, user_id),
        )
        workspace_row = cur.fetchone()

    return BootstrapResponse(
        user_id=user_id,
        workspace_id=int(workspace_row[0]),
        workspace_slug=str(workspace_row[1]),
        workspace_name=str(workspace_row[2]),
    )
