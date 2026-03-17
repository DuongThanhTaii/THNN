import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.observability import metrics_registry
from api.v1.routers import system


def test_metrics_registry_observe_and_snapshot():
    asyncio.run(
        metrics_registry.observe(
            path="/api/v1/demo",
            method="GET",
            status_code=200,
            latency_seconds=0.01,
        )
    )

    snapshot = asyncio.run(metrics_registry.snapshot())
    assert "requests_total" in snapshot
    assert "GET /api/v1/demo" in snapshot["requests_total"]


def test_system_metrics_endpoint_reports_request_counts():
    app = FastAPI()
    app.include_router(system.router)

    client = TestClient(app)

    asyncio.run(
        metrics_registry.observe(
            path="/api/v1/demo",
            method="GET",
            status_code=200,
            latency_seconds=0.01,
        )
    )

    response = client.get("/system/metrics")
    assert response.status_code == 200
    body = response.json()
    assert "requests_total" in body
    assert "GET /api/v1/demo" in body["requests_total"]
