"""Authenticated WebSocket risk alerts."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import decode_token

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        failed = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                failed.append(connection)
        for connection in failed:
            self.disconnect(connection)


manager = ConnectionManager()


async def authorized(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if origin and origin not in get_settings().cors_origins_list:
        return False
    token = websocket.cookies.get("access_token")
    if not token:
        return False
    try:
        payload = decode_token(token)
        if payload.get("type") != "access" or not payload.get("sid"):
            return False
        session = await (await get_redis()).get(f"session:{payload['sid']}")
        return bool(session and json.loads(session).get("sub") == payload.get("sub"))
    except Exception:
        return False


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    if not await authorized(websocket):
        await websocket.close(code=1008, reason="authentication required")
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"type": "pong", "message": "connected"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
