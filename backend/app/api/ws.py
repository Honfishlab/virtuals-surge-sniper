"""WebSocket routes — surge alert streaming."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.data_aggregator.aggregator import VirtualsDataAggregator
from app.processing.surge_engine import SurgeEngine

logger = logging.getLogger(__name__)

router = APIRouter()

# Connected WebSocket clients
_clients: list[WebSocket] = []


@router.websocket("/ws/surges")
async def surge_websocket(websocket: WebSocket):
    """Real-time surge alert stream.

    Clients receive JSON surge alerts instantly when detected.
    Also gets periodic health pings so clients can detect disconnects.
    """
    await websocket.accept()
    _clients.append(websocket)
    logger.info("Surge WS client connected (%d total)", len(_clients))

    try:
        # Send initial state
        surges = await _get_current_surges()
        if surges:
            await websocket.send_json({"type": "surge_alerts", "data": surges})

        # Keep alive loop
        while True:
            await websocket.send_json({"type": "ping", "ts": asyncio.get_event_loop().time()})
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        logger.info("Surge WS client disconnected")
    except Exception as exc:
        logger.error("Surge WS error: %s", exc)
    finally:
        if websocket in _clients:
            _clients.remove(websocket)


@router.websocket("/ws/tokens")
async def tokens_websocket(websocket: WebSocket):
    """Real-time token list stream (top 50)."""
    await websocket.accept()
    _clients.append(websocket)
    logger.info("Token WS client connected (%d total)", len(_clients))

    try:
        while True:
            tokens = await _get_current_tokens()
            await websocket.send_json({
                "type": "token_update",
                "count": len(tokens),
                "data": [t.model_dump() for t in tokens[:50]],
            })
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        logger.info("Token WS client disconnected")
    except Exception as exc:
        logger.error("Token WS error: %s", exc)
    finally:
        if websocket in _clients:
            _clients.remove(websocket)


async def _get_current_surges() -> list[dict]:
    """Fetch current active surges."""
    try:
        from app.api.routes import _get_aggregator
        agg = _get_aggregator()
        return await agg.get_active_surges()
    except Exception as exc:
        logger.error("Failed to fetch surges for WS: %s", exc)
        return []


async def _get_current_tokens() -> list[Any]:
    """Fetch current token list."""
    try:
        from app.api.routes import _get_aggregator
        agg = _get_aggregator()
        return await agg.get_enriched_token_list()
    except Exception as exc:
        logger.error("Failed to fetch tokens for WS: %s", exc)
        return []
