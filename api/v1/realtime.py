"""Realtime websocket endpoints."""

import asyncio
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["realtime"])

# workspace_id -> active websocket connections
_workspace_connections: dict[int, set[WebSocket]] = defaultdict(set)


@router.websocket("/workspaces/{workspace_id}")
async def workspace_socket(websocket: WebSocket, workspace_id: int) -> None:
    """Simple realtime channel for workspace-level events.

    For now this endpoint sends an initial greeting and echoes messages back
    to the client. It establishes the contract for future server pushes.
    """
    await websocket.accept()
    _workspace_connections[workspace_id].add(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "workspace_id": workspace_id,
                "message": "Realtime channel connected",
            }
        )

        while True:
            try:
                payload = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await websocket.send_json(
                    {
                        "type": "echo",
                        "workspace_id": workspace_id,
                        "payload": payload,
                    }
                )
            except TimeoutError:
                await websocket.send_json(
                    {
                        "type": "heartbeat",
                        "workspace_id": workspace_id,
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        _workspace_connections[workspace_id].discard(websocket)
        if not _workspace_connections[workspace_id]:
            del _workspace_connections[workspace_id]
