import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from messaging.platforms.esp32 import Esp32MqttPlatform


class _FakeMqttClient:
    def __init__(self):
        self.on_connect = None
        self.on_message = None
        self.published: list[tuple[str, str, int]] = []
        self.subscribed: list[str] = []
        self.username: str | None = None
        self.password: str | None = None
        self.tls_enabled = False
        self.connected = False

    def username_pw_set(self, username: str, password: str | None) -> None:
        self.username = username
        self.password = password

    def tls_set(self) -> None:
        self.tls_enabled = True

    def connect(self, *, host: str, port: int, keepalive: int) -> None:
        assert keepalive == 60
        assert host == "broker.example.com"
        assert port == 8883
        self.connected = True
        if self.on_connect is not None:
            self.on_connect(self, None, None, 0)

    def loop_start(self) -> None:
        return None

    def loop_stop(self) -> None:
        return None

    def disconnect(self) -> None:
        self.connected = False

    def subscribe(self, topic: str) -> None:
        self.subscribed.append(topic)

    def publish(self, topic: str, payload: str, qos: int) -> None:
        self.published.append((topic, payload, qos))


@pytest.mark.asyncio
async def test_esp32_platform_send_edit_delete_publish_to_command_topic():
    fake_client = _FakeMqttClient()
    platform = Esp32MqttPlatform(
        broker_url="mqtts://broker.example.com:8883",
        topic_prefix="agent",
        device_shared_secret="shared",
        mqtt_client_factory=lambda: fake_client,
    )

    await platform.start()
    message_id = await platform.send_message("device-1", "hello")
    await platform.edit_message("device-1", message_id, "updated")
    await platform.delete_message("device-1", message_id)
    await platform.stop()

    assert message_id == "esp32-out-1"
    assert fake_client.subscribed == ["agent/+/status"]
    assert len(fake_client.published) == 3
    first_topic, first_payload_raw, first_qos = fake_client.published[0]
    assert first_topic == "agent/device-1/command"
    assert first_qos == 1
    first_payload = json.loads(first_payload_raw)
    assert first_payload["action"] == "send"
    assert first_payload["text"] == "hello"


@pytest.mark.asyncio
async def test_esp32_platform_converts_status_topic_payload_to_incoming_message():
    fake_client = _FakeMqttClient()
    platform = Esp32MqttPlatform(
        broker_url="mqtts://broker.example.com:8883",
        topic_prefix="agent",
        mqtt_client_factory=lambda: fake_client,
    )
    handler = AsyncMock()
    platform.on_message(handler)

    await platform.start()
    assert fake_client.on_message is not None
    fake_client.on_message(
        fake_client,
        None,
        SimpleNamespace(
            topic="agent/device-42/status",
            payload=b'{"text":"from-device","message_id":"d-1","user_id":"u-1"}',
        ),
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    await platform.stop()

    assert handler.await_count == 1
    incoming = handler.await_args_list[0].args[0]
    assert incoming.platform == "esp32"
    assert incoming.chat_id == "device-42"
    assert incoming.user_id == "u-1"
    assert incoming.message_id == "d-1"
    assert incoming.text == "from-device"
