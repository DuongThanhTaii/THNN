"""Request tracing and in-process metrics registry."""

from __future__ import annotations

import asyncio
from collections import Counter


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._requests_total = Counter()
        self._status_total = Counter()
        self._latency_sum_seconds = Counter()

    async def observe(self, *, path: str, method: str, status_code: int, latency_seconds: float) -> None:
        route_key = f"{method.upper()} {path}"
        status_key = str(status_code)

        async with self._lock:
            self._requests_total[route_key] += 1
            self._status_total[status_key] += 1
            self._latency_sum_seconds[route_key] += max(0.0, latency_seconds)

    async def snapshot(self) -> dict:
        async with self._lock:
            return {
                "requests_total": dict(self._requests_total),
                "status_total": dict(self._status_total),
                "latency_sum_seconds": {
                    key: round(value, 6)
                    for key, value in self._latency_sum_seconds.items()
                },
            }


metrics_registry = MetricsRegistry()
