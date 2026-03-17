"""Web websocket messaging adapter integrated with realtime workspace channels."""

import asyncio
from collections.abc import Awaitable, Callable
from time import time
from typing import Any

from api.v1.realtime import (
    publish_workspace_event,
    register_workspace_client_event_handler,
    unregister_workspace_client_event_handler,
)

from ..models import IncomingMessage
from .base import MessagingPlatform


class WebPlatform(MessagingPlatform):
    """Messaging adapter that bridges websocket client events to IncomingMessage."""

    name = "web"

    def __init__(self, *, workspace_id: int = 1):
        self.workspace_id = workspace_id
        self._message_handler: Callable[[IncomingMessage], Awaitable[None]] | None = (
            None
        )
        self._connected = False
        self._out_counter = 0

    async def start(self) -> None:
        register_workspace_client_event_handler(
            self.workspace_id,
            self._handle_client_event,
        )
        self._connected = True

    async def stop(self) -> None:
        unregister_workspace_client_event_handler(
            self.workspace_id,
            self._handle_client_event,
        )
        self._connected = False

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to: str | None = None,
        parse_mode: str | None = None,
        message_thread_id: str | None = None,
    ) -> str:
        self._out_counter += 1
        message_id = f"web-out-{self._out_counter}"
        await publish_workspace_event(
            workspace_id=self.workspace_id,
            event_type="web.message.sent",
            payload={
                "chat_id": chat_id,
                "text": text,
                "reply_to": reply_to,
                "parse_mode": parse_mode,
                "message_thread_id": message_thread_id,
                "message_id": message_id,
            },
        )
        return message_id

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        parse_mode: str | None = None,
    ) -> None:
        await publish_workspace_event(
            workspace_id=self.workspace_id,
            event_type="web.message.edited",
            payload={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode,
            },
        )

    async def delete_message(
        self,
        chat_id: str,
        message_id: str,
    ) -> None:
        await publish_workspace_event(
            workspace_id=self.workspace_id,
            event_type="web.message.deleted",
            payload={
                "chat_id": chat_id,
                "message_id": message_id,
            },
        )

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

    async def _handle_client_event(self, event: dict[str, Any]) -> None:
        if not self._message_handler:
            return

        payload = event.get("payload")
        if isinstance(payload, dict):
            text_val = payload.get("text")
            if not isinstance(text_val, str) or not text_val.strip():
                return
            chat_id = str(payload.get("chat_id") or f"workspace:{self.workspace_id}")
            user_id = str(payload.get("user_id") or "web-user")
            message_id = str(
                payload.get("message_id") or f"web-in-{int(time() * 1000)}"
            )
            reply_to = payload.get("reply_to_message_id")
            message_thread_id = payload.get("message_thread_id")
            username = payload.get("username")
            incoming = IncomingMessage(
                text=text_val,
                chat_id=chat_id,
                user_id=user_id,
                message_id=message_id,
                platform="web",
                reply_to_message_id=str(reply_to) if reply_to is not None else None,
                message_thread_id=(
                    str(message_thread_id) if message_thread_id is not None else None
                ),
                username=str(username) if username is not None else None,
                raw_event=event,
            )
            await self._message_handler(incoming)
            return

        if isinstance(payload, str) and payload.strip():
            incoming = IncomingMessage(
                text=payload,
                chat_id=f"workspace:{self.workspace_id}",
                user_id="web-user",
                message_id=f"web-in-{int(time() * 1000)}",
                platform="web",
                raw_event=event,
            )
            await self._message_handler(incoming)
