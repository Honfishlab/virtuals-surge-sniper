"""API routes — FastAPI endpoints for the dashboard."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from app.api._shared import get_aggregator
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
    agg = get_aggregator()
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

        # Sort — map sort_by to the appropriate numeric attribute
        reverse = sort_order == "desc"
        sort_key_map: Dict[str, str] = {
            "alpha_score": "overall_score",
            "market_cap": "market_cap",
            "volume_24h": "volume_24h",
            "age_days": "age_days",
            "surge_score": "overall_surge_score",
        }
        sort_attr = sort_key_map.get(sort_by, "overall_score")
        if filtered:
            filtered.sort(
                key=lambda x: _get_numeric(x, sort_attr),
                reverse=reverse,
            )

        # Paginate
        result = filtered[offset : offset + limit]
        return [t.model_dump() for t in result]
    except Exception as exc:
        logger.error("get_tokens error: %s", exc)
        import traceback
        traceback.print_exc()
        return []


def _get_numeric(token: TokenData, attr: str) -> float:
    """Safely extract a numeric sort value from a token."""
    try:
        if attr == "overall_score":
            return token.alpha_score.overall_score
        if attr == "overall_surge_score":
            return token.surge.overall_surge_score
        if hasattr(token, attr):
            val = getattr(token, attr)
            if isinstance(val, float):
                return val
        if hasattr(token.price, attr):
            val = getattr(token.price, attr)
            if isinstance(val, float):
                return val
    except Exception:
        pass
    return 0.0


@router.get("/tokens/{address}", response_model=Optional[Dict[str, Any]])
async def get_token_detail(address: str):
    """Get detailed data for a single token."""
    agg = get_aggregator()
    try:
        token = await agg.get_token_detail(address)
        return token.model_dump() if token else None
    except Exception as exc:
        logger.error("get_token_detail error for %s: %s", address, exc)
        return None


@router.get("/new-tokens", response_model=List[Dict[str, Any]])
async def get_new_tokens(hours: int = Query(24, ge=1, le=168)):
    """Get tokens launched within the last N hours."""
    agg = get_aggregator()
    try:
        tokens = await agg.get_new_tokens(hours=hours)
        return [t.model_dump() for t in tokens]
    except Exception as exc:
        logger.error("get_new_tokens error: %s", exc)
        return []


@router.get("/surges", response_model=List[Dict[str, Any]])
async def get_surges():
    """Get current active surge alerts."""
    agg = get_aggregator()
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
    agg = get_aggregator()
    status = await agg.health_check()
    return HealthResponse(status=status["status"])
