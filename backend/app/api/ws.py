"""WebSocket routes — surge alert streaming."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/surges")
async def surge_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time surge alerts.

    Clients connect and receive surge alerts as they are detected.
    """
    await websocket.accept()
    try:
        import asyncio

        while True:
            await websocket.send_json({
                "type": "ping",
                "timestamp": asyncio.get_event_loop().time(),
            })
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        logger.info("Surge WebSocket disconnected")
    except Exception as exc:
        logger.error("Surge WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
