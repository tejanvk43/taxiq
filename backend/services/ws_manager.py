import asyncio
import json
from collections import defaultdict
from typing import DefaultDict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: DefaultDict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, gstin: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[gstin].add(websocket)

    async def disconnect(self, websocket: WebSocket, gstin: str) -> None:
        async with self._lock:
            if gstin in self._connections and websocket in self._connections[gstin]:
                self._connections[gstin].remove(websocket)
                if not self._connections[gstin]:
                    del self._connections[gstin]

    async def broadcast(self, gstin: str, message: dict) -> None:
        payload = json.dumps(message)
        async with self._lock:
            conns = list(self._connections.get(gstin, set()))
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                # best-effort; cleanup happens on disconnect
                pass


manager = ConnectionManager()
