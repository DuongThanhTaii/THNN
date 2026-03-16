from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import realtime


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(realtime.router)

    @app.post("/emit/{workspace_id}")
    async def emit_event(workspace_id: int):
        await realtime.publish_workspace_event(
            workspace_id=workspace_id,
            event_type="test.event",
            payload={"value": workspace_id},
        )
        return {"status": "ok"}

    return TestClient(app)


def test_websocket_sends_connected_message():
    client = _make_client()

    with client.websocket_connect("/ws/workspaces/7") as ws:
        first = ws.receive_json()

    assert first["type"] == "connected"
    assert first["workspace_id"] == 7


def test_websocket_returns_client_event_message():
    client = _make_client()

    with client.websocket_connect("/ws/workspaces/3") as ws:
        ws.receive_json()  # connected
        ws.send_text("hello-realtime")
        echoed = ws.receive_json()

    assert echoed["type"] == "client_event"
    assert echoed["workspace_id"] == 3
    assert echoed["payload"] == "hello-realtime"


def test_publish_workspace_event_reaches_websocket_subscriber():
    client = _make_client()

    with client.websocket_connect("/ws/workspaces/5") as ws:
        ws.receive_json()  # connected

        emit_response = client.post("/emit/5")
        assert emit_response.status_code == 200

        event_message = ws.receive_json()

    assert event_message["type"] == "event"
    assert event_message["workspace_id"] == 5
    assert event_message["event_type"] == "test.event"
    assert event_message["payload"] == {"value": 5}
