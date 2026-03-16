"""Realtime websocket endpoints and event broadcasting helpers."""

import asyncio
import contextlib
from collections import defaultdict
from dataclasses import dataclass, field
from time import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["realtime"])

HEARTBEAT_INTERVAL_S = 30.0
QUEUE_MAX_SIZE = 100


@dataclass(eq=False)
class _WorkspaceSubscriber:
    websocket: WebSocket
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=QUEUE_MAX_SIZE)
    )


# workspace_id -> active websocket subscribers
_workspace_connections: dict[int, set[_WorkspaceSubscriber]] = defaultdict(set)


async def publish_workspace_event(
    workspace_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Broadcast an event payload to all websocket clients of one workspace."""
    subscribers = list(_workspace_connections.get(workspace_id, set()))
    if not subscribers:
        return

    message = {
        "type": "event",
        "event_type": event_type,
        "workspace_id": workspace_id,
        "timestamp": time(),
        "payload": payload,
    }

    for subscriber in subscribers:
        try:
            subscriber.queue.put_nowait(message)
        except asyncio.QueueFull:
            with contextlib.suppress(asyncio.QueueEmpty):
                subscriber.queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                subscriber.queue.put_nowait(message)
                # If still full, event is dropped for this slow subscriber.


async def _sender_loop(subscriber: _WorkspaceSubscriber, workspace_id: int) -> None:
    while True:
        try:
            message = await asyncio.wait_for(
                subscriber.queue.get(),
                timeout=HEARTBEAT_INTERVAL_S,
            )
            await subscriber.websocket.send_json(message)
        except TimeoutError:
            await subscriber.websocket.send_json(
                {
                    "type": "heartbeat",
                    "workspace_id": workspace_id,
                    "timestamp": time(),
                }
            )


async def _receiver_loop(subscriber: _WorkspaceSubscriber, workspace_id: int) -> None:
    while True:
        data = await subscriber.websocket.receive_text()
        await subscriber.queue.put(
            {
                "type": "client_event",
                "workspace_id": workspace_id,
                "timestamp": time(),
                "payload": data,
            }
        )


@router.websocket("/workspaces/{workspace_id}")
async def workspace_socket(websocket: WebSocket, workspace_id: int) -> None:
    """Workspace realtime channel with server-push events and heartbeat."""
    await websocket.accept()
    subscriber = _WorkspaceSubscriber(websocket=websocket)
    _workspace_connections[workspace_id].add(subscriber)

    await websocket.send_json(
        {
            "type": "connected",
            "workspace_id": workspace_id,
            "message": "Realtime channel connected",
            "timestamp": time(),
        }
    )

    sender_task = asyncio.create_task(_sender_loop(subscriber, workspace_id))
    receiver_task = asyncio.create_task(_receiver_loop(subscriber, workspace_id))

    try:
        done, pending = await asyncio.wait(
            {sender_task, receiver_task},
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in done:
            task.result()
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        receiver_task.cancel()
        _workspace_connections[workspace_id].discard(subscriber)
        if not _workspace_connections[workspace_id]:
            del _workspace_connections[workspace_id]
