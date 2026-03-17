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


class AutomationCreateRequest(BaseModel):
    workspace_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    trigger_type: str = Field(min_length=1, max_length=100)
    action_type: str = Field(min_length=1, max_length=100)
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class AutomationUpdateRequest(BaseModel):
    workspace_id: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    trigger_type: str | None = Field(default=None, min_length=1, max_length=100)
    action_type: str | None = Field(default=None, min_length=1, max_length=100)
    config: dict | None = None
    enabled: bool | None = None


class AutomationResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    trigger_type: str
    action_type: str
    config: dict
    enabled: bool


class BootstrapResponse(BaseModel):
    user_id: int
    workspace_id: int
    workspace_slug: str
    workspace_name: str


class SyncConflictSummary(BaseModel):
    id: int
    source_system: str
    target_system: str
    entity_ref: str
    reason: str
    status: str
    created_at: str
    resolved_at: str | None


class SyncStatusProjectionResponse(BaseModel):
    workspace_id: int
    health: str
    policies_total: int
    policies_enabled: int
    conflicts_open: int
    conflicts_resolved: int
    last_conflict_at: str | None
    recent_conflicts: list[SyncConflictSummary]
