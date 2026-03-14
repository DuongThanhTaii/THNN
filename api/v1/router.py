"""Router aggregator for API v1 and webhooks."""

from fastapi import APIRouter

from .realtime import router as realtime_router
from .routers.auth import router as auth_router
from .routers.automations import router as automations_router
from .routers.integrations import router as integrations_router
from .routers.providers import router as providers_router
from .routers.system import router as system_router
from .routers.tasks import router as tasks_router
from .routers.webhooks import router as webhooks_router
from .routers.workspaces import router as workspaces_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(system_router)
v1_router.include_router(auth_router)
v1_router.include_router(workspaces_router)
v1_router.include_router(tasks_router)
v1_router.include_router(automations_router)
v1_router.include_router(integrations_router)
v1_router.include_router(providers_router)

# Webhooks are intentionally outside /api/v1.
root_webhook_router = APIRouter()
root_webhook_router.include_router(webhooks_router)
root_webhook_router.include_router(realtime_router)
