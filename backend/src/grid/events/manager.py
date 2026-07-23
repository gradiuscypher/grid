import uuid
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """In-process registry of live `/ws/cases/{id}` subscribers. Paired with the
    pg LISTEN/NOTIFY bridge in `listener.py` so any process's event becomes
    visible to every other process's WS clients (ARCHITECTURE §4)."""

    def __init__(self) -> None:
        self._subscribers: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    def subscribe(self, case_id: uuid.UUID, websocket: WebSocket) -> None:
        self._subscribers[case_id].add(websocket)

    def unsubscribe(self, case_id: uuid.UUID, websocket: WebSocket) -> None:
        self._subscribers[case_id].discard(websocket)
        if not self._subscribers[case_id]:
            del self._subscribers[case_id]

    async def broadcast(self, case_id: uuid.UUID, message: dict[str, Any]) -> None:
        for websocket in list(self._subscribers.get(case_id, ())):
            try:
                await websocket.send_json(message)
            except Exception:
                self.unsubscribe(case_id, websocket)


connection_manager = ConnectionManager()
