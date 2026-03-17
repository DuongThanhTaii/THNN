"""HTTP rate limiting middleware for user/workspace/channel scopes."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from config.settings import get_settings


@dataclass(frozen=True, slots=True)
class _LimitConfig:
    limit: int
    window_seconds: int


class _RateWindowStore:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str, config: _LimitConfig) -> tuple[bool, float]:
        now = time.monotonic()
        window_start = now - float(config.window_seconds)

        async with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= config.limit:
                retry_after = max(0.0, (bucket[0] + config.window_seconds) - now)
                return False, retry_after

            bucket.append(now)
            return True, 0.0


_store = _RateWindowStore()


def _scope_values(request: Request) -> dict[str, str]:
    query = request.query_params
    headers = request.headers

    user_id = (
        headers.get("x-user-id")
        or query.get("user_id")
        or query.get("owner_user_id")
        or ""
    ).strip()
    workspace_id = (
        headers.get("x-workspace-id")
        or query.get("workspace_id")
        or ""
    ).strip()
    channel_id = (
        headers.get("x-channel-id")
        or headers.get("x-platform")
        or query.get("channel_id")
        or query.get("chat_id")
        or ""
    ).strip()

    return {
        "user": user_id,
        "workspace": workspace_id,
        "channel": channel_id,
    }


def _configs() -> dict[str, _LimitConfig]:
    settings = get_settings()
    return {
        "user": _LimitConfig(
            limit=settings.rate_limit_user_limit,
            window_seconds=settings.rate_limit_user_window,
        ),
        "workspace": _LimitConfig(
            limit=settings.rate_limit_workspace_limit,
            window_seconds=settings.rate_limit_workspace_window,
        ),
        "channel": _LimitConfig(
            limit=settings.rate_limit_channel_limit,
            window_seconds=settings.rate_limit_channel_window,
        ),
    }


async def enforce_rate_limits(request: Request, call_next):
    settings = get_settings()
    if not settings.rate_limit_enforce:
        return await call_next(request)

    if not (request.url.path.startswith("/api/") or request.url.path.startswith("/v1/")):
        return await call_next(request)

    scope_values = _scope_values(request)
    scope_configs = _configs()

    for scope_name, scope_value in scope_values.items():
        if not scope_value:
            continue
        allowed, retry_after = await _store.allow(
            key=f"{scope_name}:{scope_value}",
            config=scope_configs[scope_name],
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "type": "error",
                    "error": {
                        "type": "rate_limit_error",
                        "message": (
                            f"rate limit exceeded for {scope_name} scope"
                        ),
                        "scope": scope_name,
                        "scope_value": scope_value,
                        "retry_after_seconds": round(retry_after, 3),
                    },
                },
                headers={"Retry-After": str(max(1, int(retry_after) if retry_after else 1))},
            )

    return await call_next(request)
