from typing import Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                to_remove.append(connection)
        for c in to_remove:
            self.disconnect(c)


manager = ConnectionManager()

