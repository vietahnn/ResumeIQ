import logging
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("BotConnectionManager")


class ConnectionManager:
    def __init__(self):
        self._active_connections: Dict[str, Set[WebSocket]] = {}

    # Registers an incoming WebSocket connection into the session pool
    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self._active_connections:
            self._active_connections[session_id] = set()
        self._active_connections[session_id].add(websocket)
        logger.info("WebSocket connected for session: %s. Active: %d", session_id, len(self._active_connections[session_id]))

    # Removes a disconnected WebSocket from the session pool
    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self._active_connections:
            self._active_connections[session_id].discard(websocket)
            if not self._active_connections[session_id]:
                del self._active_connections[session_id]
        logger.info("WebSocket disconnected for session: %s", session_id)

    # Broadcasts a JSON message payload to all active clients of a specific session
    async def send_json(self, session_id: str, message: Dict[str, Any]) -> None:
        if session_id not in self._active_connections:
            return

        dead_connections = set()
        for ws in self._active_connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception as err:
                logger.warning("Failed to send message to WebSocket: %s", err)
                dead_connections.add(ws)

        for ws in dead_connections:
            self.disconnect(session_id, ws)


ws_manager = ConnectionManager()
