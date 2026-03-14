"""Automation endpoints scaffold."""

from fastapi import APIRouter

from api.v1.schemas import GenericMessageResponse

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("", response_model=GenericMessageResponse)
async def list_automations() -> GenericMessageResponse:
    return GenericMessageResponse(
        status="todo",
        message="Automation listing endpoint scaffolded.",
    )
