from unittest.mock import AsyncMock

import pytest

from messaging.platforms.web import WebPlatform


@pytest.mark.asyncio
async def test_web_platform_send_edit_delete_publish_events(monkeypatch):
    published = []

    async def fake_publish(workspace_id: int, event_type: str, payload: dict):
        published.append((workspace_id, event_type, payload))

    monkeypatch.setattr("messaging.platforms.web.publish_workspace_event", fake_publish)

    platform = WebPlatform(workspace_id=9)
    msg_id = await platform.send_message("chat-a", "hello")
    await platform.edit_message("chat-a", msg_id, "hello-2")
    await platform.delete_message("chat-a", msg_id)

    assert msg_id == "web-out-1"
    assert published[0][0] == 9
    assert published[0][1] == "web.message.sent"
    assert published[1][1] == "web.message.edited"
    assert published[2][1] == "web.message.deleted"


@pytest.mark.asyncio
async def test_web_platform_start_stop_registers_handler(monkeypatch):
    register_calls = []
    unregister_calls = []

    monkeypatch.setattr(
        "messaging.platforms.web.register_workspace_client_event_handler",
        lambda workspace_id, handler: register_calls.append((workspace_id, handler)),
    )
    monkeypatch.setattr(
        "messaging.platforms.web.unregister_workspace_client_event_handler",
        lambda workspace_id, handler: unregister_calls.append((workspace_id, handler)),
    )

    platform = WebPlatform(workspace_id=3)
    await platform.start()
    await platform.stop()

    assert platform.is_connected is False
    assert len(register_calls) == 1
    assert len(unregister_calls) == 1


@pytest.mark.asyncio
async def test_web_platform_converts_client_payload_to_incoming_message():
    platform = WebPlatform(workspace_id=4)
    handler = AsyncMock()
    platform.on_message(handler)

    await platform._handle_client_event(
        {
            "workspace_id": 4,
            "payload": {
                "text": "from-web",
                "chat_id": "room-1",
                "user_id": "u-1",
                "message_id": "m-1",
                "reply_to_message_id": "m-0",
            },
        }
    )

    assert handler.await_count == 1
    incoming = handler.await_args_list[0].args[0]
    assert incoming.platform == "web"
    assert incoming.chat_id == "room-1"
    assert incoming.user_id == "u-1"
    assert incoming.message_id == "m-1"
    assert incoming.reply_to_message_id == "m-0"
    assert incoming.text == "from-web"
