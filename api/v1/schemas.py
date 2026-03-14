"""Pydantic schemas for API v1 endpoints."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    provider: str
    environment: str


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    workspace_id: int = Field(ge=1)


class TaskResponse(BaseModel):
    id: int
    workspace_id: int
    title: str
    description: str | None
    status: str
    priority: str


class TaskUpdateRequest(BaseModel):
    workspace_id: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: str | None = None
    priority: str | None = None


class GenericMessageResponse(BaseModel):
    status: str
    message: str


class BootstrapResponse(BaseModel):
    user_id: int
    workspace_id: int
    workspace_slug: str
    workspace_name: str
