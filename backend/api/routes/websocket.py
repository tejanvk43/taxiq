import asyncio
import json
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.ws_manager import manager

router = APIRouter(prefix="", tags=["websocket"])


async def _demo_event_stream(gstin: str) -> None:
    """
    Emits a repeating sequence of high-signal demo events for the ticker/graph.
    Only runs while the client is connected (task is cancelled on disconnect).
    """
    events = [
        {"type": "FRAUD_ALERT", "payload": {"ringId": "RING-001", "confidence": 0.84, "amount": 8420000}},
        {"type": "NEW_MISMATCH", "payload": {"invoiceId": "INV-2024-001", "severity": 92, "amount": 99900}},
        {"type": "SCORE_UPDATE", "payload": {"gstin": "19AABCG1234Q1Z2", "oldScore": 24, "newScore": 18, "trend": "DOWN"}},
        {"type": "ITC_RECOVERED", "payload": {"amount": 65000, "vendor": "Zenith Metals"}},
    ]
    i = 0
    while True:
        await manager.broadcast(gstin, events[i % len(events)])
        i += 1
        await asyncio.sleep(12)


@router.websocket("/ws/alerts/{gstin}")
async def websocket_alerts(websocket: WebSocket, gstin: str):
    await manager.connect(websocket, gstin)
    task = asyncio.create_task(_demo_event_stream(gstin))
    try:
        while True:
            _ = await websocket.receive_text()
            # Keepalive / ignore client messages for now
    except WebSocketDisconnect:
        task.cancel()
        await manager.disconnect(websocket, gstin)
