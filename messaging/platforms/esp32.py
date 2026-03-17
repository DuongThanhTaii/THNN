"""ESP32 MQTT platform adapter using command/status topics."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from time import time
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from ..models import IncomingMessage
from .base import MessagingPlatform

_mqtt_module: Any = None
try:
    import paho.mqtt.client as _mqtt_import

    _mqtt_module = _mqtt_import
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False


def _get_mqtt_module() -> Any:
    if not MQTT_AVAILABLE or _mqtt_module is None:
        raise ImportError("paho-mqtt is required. Install with: pip install paho-mqtt")
    return _mqtt_module


def _parse_broker_url(broker_url: str) -> tuple[str, int, bool]:
    parsed = urlparse(broker_url)
    host = parsed.hostname
    if not host:
        raise ValueError(f"Invalid ESP32 broker URL: {broker_url!r}")
    use_tls = parsed.scheme == "mqtts"
    default_port = 8883 if use_tls else 1883
    port = parsed.port if parsed.port is not None else default_port
    return host, port, use_tls


class Esp32MqttPlatform(MessagingPlatform):
    """Messaging platform that bridges ESP32 device status and commands over MQTT."""

    name = "esp32"

    def __init__(
        self,
        *,
        broker_url: str,
        username: str | None = None,
        password: str | None = None,
        topic_prefix: str = "agent",
        device_shared_secret: str | None = None,
        mqtt_client_factory: Callable[[], Any] | None = None,
    ):
        self.broker_url = broker_url
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix.strip("/") or "agent"
        self.device_shared_secret = device_shared_secret
        self._mqtt_client_factory = mqtt_client_factory
        self._client: Any | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = False
        self._message_handler: Callable[[IncomingMessage], Awaitable[None]] | None = (
            None
        )
        self._out_counter = 0

    async def start(self) -> None:
        host, port, use_tls = _parse_broker_url(self.broker_url)
        self._loop = asyncio.get_running_loop()
        self._client = self._create_client()
        if self.username:
            self._client.username_pw_set(self.username, self.password)
        if use_tls:
            self._client.tls_set()
        self._client.on_connect = self._on_mqtt_connect
        self._client.on_message = self._on_mqtt_message
        self._client.connect(host=host, port=port, keepalive=60)
        self._client.loop_start()
        self._connected = True
        logger.info("ESP32 MQTT platform started")

    async def stop(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
        self._connected = False
        logger.info("ESP32 MQTT platform stopped")

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to: str | None = None,
        parse_mode: str | None = None,
        message_thread_id: str | None = None,
    ) -> str:
        self._out_counter += 1
        message_id = f"esp32-out-{self._out_counter}"
        payload = {
            "action": "send",
            "message_id": message_id,
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to,
            "parse_mode": parse_mode,
            "message_thread_id": message_thread_id,
            "shared_secret": self.device_shared_secret,
        }
        self._publish_json(self._command_topic(chat_id), payload)
        return message_id

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        parse_mode: str | None = None,
    ) -> None:
        payload = {
            "action": "edit",
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "shared_secret": self.device_shared_secret,
        }
        self._publish_json(self._command_topic(chat_id), payload)

    async def delete_message(
        self,
        chat_id: str,
        message_id: str,
    ) -> None:
        payload = {
            "action": "delete",
            "chat_id": chat_id,
            "message_id": message_id,
            "shared_secret": self.device_shared_secret,
        }
        self._publish_json(self._command_topic(chat_id), payload)

    async def queue_send_message(
        self,
        chat_id: str,
        text: str,
        reply_to: str | None = None,
        parse_mode: str | None = None,
        fire_and_forget: bool = True,
        message_thread_id: str | None = None,
    ) -> str | None:
        coroutine = self.send_message(
            chat_id=chat_id,
            text=text,
            reply_to=reply_to,
            parse_mode=parse_mode,
            message_thread_id=message_thread_id,
        )
        if fire_and_forget:
            self.fire_and_forget(coroutine)
            return None
        return await coroutine

    async def queue_edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        parse_mode: str | None = None,
        fire_and_forget: bool = True,
    ) -> None:
        coroutine = self.edit_message(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
        )
        if fire_and_forget:
            self.fire_and_forget(coroutine)
            return
        await coroutine

    async def queue_delete_message(
        self,
        chat_id: str,
        message_id: str,
        fire_and_forget: bool = True,
    ) -> None:
        coroutine = self.delete_message(chat_id=chat_id, message_id=message_id)
        if fire_and_forget:
            self.fire_and_forget(coroutine)
            return
        await coroutine

    def on_message(
        self,
        handler: Callable[[IncomingMessage], Awaitable[None]],
    ) -> None:
        self._message_handler = handler

    def fire_and_forget(self, task: Awaitable[Any]) -> None:
        async def _runner() -> None:
            await task

        task_ref = asyncio.create_task(_runner())
        task_ref.add_done_callback(lambda t: t.exception() if t.done() else None)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _create_client(self) -> Any:
        if self._mqtt_client_factory is not None:
            return self._mqtt_client_factory()
        mqtt = _get_mqtt_module()
        return mqtt.Client()

    def _status_topic_pattern(self) -> str:
        return f"{self.topic_prefix}/+/status"

    def _command_topic(self, chat_id: str) -> str:
        return f"{self.topic_prefix}/{chat_id}/command"

    def _on_mqtt_connect(self, client: Any, userdata: Any, flags: Any, rc: int) -> None:
        if rc != 0:
            logger.warning(f"ESP32 MQTT connect failed with rc={rc}")
            return
        client.subscribe(self._status_topic_pattern())

    def _on_mqtt_message(self, client: Any, userdata: Any, msg: Any) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(
            self._schedule_handle_status,
            msg.topic,
            msg.payload,
        )

    def _schedule_handle_status(self, topic: str, payload: bytes) -> None:
        task = asyncio.create_task(self._handle_status_message(topic, payload))
        task.add_done_callback(lambda t: t.exception() if t.done() else None)

    async def _handle_status_message(self, topic: str, payload: bytes) -> None:
        if not self._message_handler:
            return

        topic_parts = topic.split("/")
        if len(topic_parts) < 3:
            return
        device_id = topic_parts[-2]

        decoded = payload.decode("utf-8", errors="replace").strip()
        payload_data: dict[str, Any] | str
        text: str
        if not decoded:
            return

        try:
            parsed_json = json.loads(decoded)
        except json.JSONDecodeError:
            payload_data = decoded
            text = decoded
            chat_id = device_id
            user_id = f"esp32:{device_id}"
            message_id = f"esp32-in-{int(time() * 1000)}"
            reply_to_message_id: str | None = None
            message_thread_id: str | None = None
            username: str | None = None
        else:
            payload_data = parsed_json
            if not isinstance(parsed_json, dict):
                return
            text_raw = parsed_json.get("text")
            if not isinstance(text_raw, str) or not text_raw.strip():
                return
            text = text_raw
            chat_id = str(parsed_json.get("chat_id") or device_id)
            user_id = str(parsed_json.get("user_id") or f"esp32:{device_id}")
            message_id = str(
                parsed_json.get("message_id") or f"esp32-in-{int(time() * 1000)}"
            )
            reply_to_raw = parsed_json.get("reply_to_message_id")
            thread_raw = parsed_json.get("message_thread_id")
            username_raw = parsed_json.get("username")
            reply_to_message_id = (
                str(reply_to_raw) if reply_to_raw is not None else None
            )
            message_thread_id = str(thread_raw) if thread_raw is not None else None
            username = str(username_raw) if username_raw is not None else None

        incoming = IncomingMessage(
            text=text,
            chat_id=chat_id,
            user_id=user_id,
            message_id=message_id,
            platform="esp32",
            reply_to_message_id=reply_to_message_id,
            message_thread_id=message_thread_id,
            username=username,
            raw_event={"topic": topic, "payload": payload_data},
        )
        await self._message_handler(incoming)

    def _publish_json(self, topic: str, payload: dict[str, Any]) -> None:
        if self._client is None:
            raise RuntimeError("ESP32 MQTT client is not connected")
        self._client.publish(topic, json.dumps(payload), qos=1)
