"""API routes — FastAPI endpoints for the dashboard."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import settings
from app.data_aggregator.aggregator import VirtualsDataAggregator
from app.models import (
    ErrorResponse,
    FilterParams,
    HealthResponse,
    SnipeRequest,
    SnipeResponse,
    TokenData,
)

logger = logging.getLogger(__name__)

router = APIRouter()
ws_router = APIRouter()

# Singleton aggregator (initialized on first request)
_aggregator: Optional[VirtualsDataAggregator] = None


def _get_aggregator() -> VirtualsDataAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = VirtualsDataAggregator()
    return _aggregator


# ── Token Endpoints ─────────────────────────────────────────────────────

@router.get("/tokens", response_model=List[Dict[str, Any]])
async def get_tokens(
    status: Optional[str] = Query(None, description="on_curve | graduated"),
    is_surging: Optional[bool] = Query(None, description="Only surging tokens"),
    min_age_days: Optional[float] = Query(None),
    max_age_days: Optional[float] = Query(None),
    min_alpha: Optional[float] = Query(None, alias="min_alpha_score"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("alpha_score", description="Sort field"),
    sort_order: str = Query("desc", description="asc | desc"),
):
    """Get enriched token list with optional filters."""
    agg = _get_aggregator()
    try:
        tokens = await agg.get_enriched_token_list()

        # Apply filters
        filtered: List[TokenData] = []
        for t in tokens:
            if status and t.token_type.value != status:
                continue
            if is_surging and not t.surge.is_surging:
                continue
            if min_age_days is not None and t.age_days < min_age_days:
                continue
            if max_age_days is not None and t.age_days > max_age_days:
                continue
            if min_alpha is not None and t.alpha_score.overall_score < min_alpha:
                continue
            filtered.append(t)

        # Sort
        reverse = sort_order == "desc"
        if hasattr(filtered[0], sort_by) if filtered else False:
            filtered.sort(
                key=lambda x: getattr(x, sort_by, 0) if hasattr(x, sort_by) else 0,
                reverse=reverse,
            )

        # Paginate
        result = filtered[offset : offset + limit]
        return [t.model_dump() for t in result]
    except Exception as exc:
        logger.error("get_tokens error: %s", exc)
        return []


@router.get("/tokens/{address}", response_model=Optional[Dict[str, Any]])
async def get_token_detail(address: str):
    """Get detailed data for a single token."""
    agg = _get_aggregator()
    try:
        token = await agg.get_token_detail(address)
        return token.model_dump() if token else None
    except Exception as exc:
        logger.error("get_token_detail error for %s: %s", address, exc)
        return None


@router.get("/new-tokens", response_model=List[Dict[str, Any]])
async def get_new_tokens(hours: int = Query(24, ge=1, le=168)):
    """Get tokens launched within the last N hours."""
    agg = _get_aggregator()
    try:
        tokens = await agg.get_new_tokens(hours=hours)
        return [t.model_dump() for t in tokens]
    except Exception as exc:
        logger.error("get_new_tokens error: %s", exc)
        return []


@router.get("/surges", response_model=List[Dict[str, Any]])
async def get_surges():
    """Get current active surge alerts."""
    agg = _get_aggregator()
    try:
        return await agg.get_active_surges()
    except Exception as exc:
        logger.error("get_surges error: %s", exc)
        return []


@router.post("/snipe", response_model=SnipeResponse)
async def trigger_snipe(request: SnipeRequest):
    """Trigger surge sniper execution (simulation or live).

    In simulation mode, returns expected cost/output/gas without executing.
    Set execute=true for live execution (requires wallet config).
    """
    if settings.snipe_simulation_mode or not request.execute:
        return SnipeResponse(
            success=True,
            simulation=True,
            token_address=request.token_address,
            estimated_cost=request.amount_virtual,
            estimated_output=request.amount_virtual * 1.0,
            gas_estimate=150000,
            message="Simulation mode — no execution. Set execute=true for live execution.",
        )

    # Live execution would go here
    return SnipeResponse(
        success=False,
        simulation=False,
        token_address=request.token_address,
        estimated_cost=request.amount_virtual,
        estimated_output=0.0,
        message="Live execution not yet implemented.",
    )


# ── Health ──────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    agg = _get_aggregator()
    status = await agg.health_check()
    return HealthResponse(status=status["status"])


# ── WebSocket ───────────────────────────────────────────────────────────

@ws_router.websocket("/ws/surges")
async def surge_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time surge alerts.

    Clients subscribe and receive surge alerts as they are detected.
    """
    await websocket.accept()
    try:
        agg = _get_aggregator()

        # Subscribe to a minimal polling loop for surges
        import asyncio

        while True:
            surges = await agg.get_active_surges()
            if surges:
                await websocket.send_json({
                    "type": "surge_alerts",
                    "data": surges,
                })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("Surge WebSocket disconnected")
    except Exception as exc:
        logger.error("Surge WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass


@ws_router.websocket("/ws/tokens")
async def tokens_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time token updates.

    Sends full token list updates on a configurable interval.
    """
    await websocket.accept()
    try:
        agg = _get_aggregator()
        import asyncio

        while True:
            tokens = await agg.get_enriched_token_list()
            await websocket.send_json({
                "type": "token_update",
                "count": len(tokens),
                "data": [t.model_dump() for t in tokens[:50]],  # top 50
            })
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        logger.info("Token WebSocket disconnected")
    except Exception as exc:
        logger.error("Token WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
