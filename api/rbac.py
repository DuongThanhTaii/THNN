"""Role-based access control middleware helpers."""

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from config.settings import get_settings

READ_ROLES = {"viewer", "member", "admin", "owner"}
WRITE_ROLES = {"member", "admin", "owner"}
ADMIN_ROLES = {"admin", "owner"}

_WORKSPACE_PATH_RE = re.compile(r"^/api/v1/workspaces/(\d+)$")


def _is_enabled() -> bool:
    settings = get_settings()
    return bool(getattr(settings, "rbac_enforce", False))


def _extract_workspace_from_path(path: str) -> int | None:
    match = _WORKSPACE_PATH_RE.match(path)
    if not match:
        return None
    return int(match.group(1))


def _extract_workspace_from_payload(payload: dict[str, Any] | None) -> int | None:
    if not payload:
        return None
    workspace_id = payload.get("workspace_id")
    if workspace_id is None:
        return None
    return int(workspace_id)


def _resolve_policy(path: str, method: str) -> tuple[set[str] | None, bool]:
    normalized = method.upper()

    if path.startswith("/api/v1/tasks") or path.startswith("/api/v1/automations"):
        if normalized == "GET":
            return READ_ROLES, True
        if normalized in {"POST", "PATCH", "DELETE"}:
            return WRITE_ROLES, True

    if path == "/api/v1/workspaces":
        if normalized == "GET":
            return READ_ROLES, False
        if normalized == "POST":
            return ADMIN_ROLES, False

    if _WORKSPACE_PATH_RE.match(path) and normalized == "DELETE":
        return ADMIN_ROLES, True

    return None, False


def _parse_role(request: Request, allowed_roles: set[str]) -> None:
    role = request.headers.get("x-user-role", "").strip().lower()
    if not role:
        raise HTTPException(status_code=401, detail="missing x-user-role header")
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="insufficient role")


def _parse_workspace_scope(
    request: Request, requested_workspace_id: int | None
) -> None:
    if requested_workspace_id is None:
        return

    scope_header = request.headers.get("x-workspace-id", "").strip()
    if not scope_header:
        raise HTTPException(status_code=401, detail="missing x-workspace-id header")

    try:
        scoped_workspace_id = int(scope_header)
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail="invalid x-workspace-id header"
        ) from e

    if scoped_workspace_id != requested_workspace_id:
        raise HTTPException(status_code=403, detail="workspace scope mismatch")


async def _extract_json_payload(
    request: Request,
) -> tuple[dict[str, Any] | None, bytes]:
    body_bytes = await request.body()
    if not body_bytes:
        return None, body_bytes

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return None, body_bytes

    if isinstance(payload, dict):
        return payload, body_bytes
    return None, body_bytes


def _request_with_replay_body(request: Request, body_bytes: bytes) -> Request:
    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    return Request(request.scope, receive)


async def enforce_rbac(
    request: Request,
    call_next: Callable[[Request], Awaitable[Any]],
):
    if not _is_enabled():
        return await call_next(request)

    path = request.url.path
    method = request.method
    allowed_roles, requires_workspace_scope = _resolve_policy(path, method)
    if allowed_roles is None:
        return await call_next(request)

    try:
        _parse_role(request, allowed_roles)

        payload, body_bytes = await _extract_json_payload(request)
        requested_workspace_id = None

        if requires_workspace_scope:
            requested_workspace_id = (
                _extract_workspace_from_payload(payload)
                or request.query_params.get("workspace_id")
                or _extract_workspace_from_path(path)
            )

            if isinstance(requested_workspace_id, str):
                try:
                    requested_workspace_id = int(requested_workspace_id)
                except ValueError as e:
                    raise HTTPException(
                        status_code=422,
                        detail="invalid workspace_id",
                    ) from e

            _parse_workspace_scope(request, requested_workspace_id)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    replay_request = _request_with_replay_body(request, body_bytes)
    return await call_next(replay_request)
