"""Provider profile endpoints scaffold."""

from fastapi import APIRouter

from api.v1.schemas import GenericMessageResponse
from config.settings import get_settings

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/current", response_model=dict)
async def current_provider() -> dict:
    settings = get_settings()
    return {
        "provider": settings.provider_type,
        "model": settings.model_name,
        "fallback_model": settings.model,
    }


@router.post("/test", response_model=GenericMessageResponse)
async def test_provider() -> GenericMessageResponse:
    return GenericMessageResponse(
        status="todo",
        message="Provider test endpoint scaffolded. Integrate actual test call next.",
    )
