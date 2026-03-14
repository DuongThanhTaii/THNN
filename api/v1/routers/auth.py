"""Auth API skeleton."""

from fastapi import APIRouter

from api.v1.schemas import GenericMessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=GenericMessageResponse)
async def login() -> GenericMessageResponse:
    return GenericMessageResponse(
        status="todo",
        message="Auth login flow is scaffolded and awaiting implementation.",
    )


@router.post("/refresh", response_model=GenericMessageResponse)
async def refresh() -> GenericMessageResponse:
    return GenericMessageResponse(
        status="todo",
        message="Token refresh flow is scaffolded and awaiting implementation.",
    )
