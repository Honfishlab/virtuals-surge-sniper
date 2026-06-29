"""Pydantic models for tokens, metrics, and API responses."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class TokenType(str, Enum):
    ON_CURVE = "on_curve"
    GRADUATED = "graduated"


class TokenStatus(str, Enum):
    ACTIVE = "active"
    SLEEPING = "sleeping"


class UsageMetrics(BaseModel):
    acp_jobs_24h: int = 0
    acp_jobs_total: int = 0
    inference_calls_24h: int = 0
    micro_payments_24h: int = 0
    estimated_revenue_usd: float = 0.0


class BondingCurveMetrics(BaseModel):
    progress_percent: float = 0.0
    bonding_value_virtual: float = 0.0
    current_supply: int = 0
    total_supply: int = 10_000_000
    current_price: float = 0.0
    estimated_graduation_time: datetime | None = None
    is_on_curve: bool = True
    is_graduated: bool = False


class PriceMetrics(BaseModel):
    current_price: float = 0.0
    price_24h_ago: float = 0.0
    price_change_24h: float = 0.0
    market_cap: float = 0.0
    fdv: float = 0.0
    liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    volume_7d: float = 0.0


class SurgeMetrics(BaseModel):
    volume_multiplier: float = 1.0
    activity_multiplier: float = 1.0
    overall_surge_score: float = 0.0
    is_surging: bool = False
    last_surge_detected: datetime | None = None


class AlphaScoreResult(BaseModel):
    overall_score: float = 0.0  # 0-100
    surge_component: float = 0.0
    usage_component: float = 0.0
    bonding_component: float = 0.0
    trend_component: float = 0.0
    custom_weight: float = 1.0


class TokenData(BaseModel):
    """Complete token data with all metrics."""

    address: str
    name: str
    symbol: str = ""
    agent_id: str = ""
    creator: str = ""
    description: str = ""
    logo_url: str = ""
    links: dict = Field(default_factory=dict)

    status: TokenStatus = TokenStatus.ACTIVE
    token_type: TokenType = TokenType.ON_CURVE

    age_days: float = 0.0
    launched_at: datetime | None = None

    bonding: BondingCurveMetrics = Field(default_factory=BondingCurveMetrics)
    price: PriceMetrics = Field(default_factory=PriceMetrics)
    surge: SurgeMetrics = Field(default_factory=SurgeMetrics)
    usage: UsageMetrics = Field(default_factory=UsageMetrics)

    alpha_score: AlphaScoreResult = Field(default_factory=AlphaScoreResult)

    # Agent treasury / accumulation proxy
    accumulated_virtual: float = 0.0
    treasury_revenue_usd: float = 0.0


class TokenListItem(BaseModel):
    """Compact view for the table listing."""

    address: str
    name: str
    symbol: str = ""
    age_days: float = 0.0
    bonding_progress: float = 0.0
    bonding_value_virtual: float = 0.0
    current_price: float = 0.0
    market_cap: float = 0.0
    surge_multiplier: float = 0.0
    usage_score: int = 0
    alpha_score: float = 0.0
    is_surging: bool = False
    token_type: TokenType = TokenType.ON_CURVE
    status: TokenStatus = TokenStatus.ACTIVE


class SurgeAlert(BaseModel):
    """Real-time surge alert."""

    token_address: str
    token_name: str
    surge_type: str  # volume, activity, or combined
    surge_score: float
    surge_multiplier: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: str = ""


class FilterParams(BaseModel):
    """Query filters for /api/tokens."""

    status: TokenType | None = None  # on_curve | graduated
    is_surging: bool | None = None
    min_age_days: float | None = None
    max_age_days: float | None = None
    min_alpha_score: float | None = None
    limit: int = 100
    offset: int = 0
    sort_by: str = "alpha_score"
    sort_order: str = "desc"


class SnipeRequest(BaseModel):
    """Request to trigger a surge sniper execution."""

    token_address: str
    amount_virtual: float
    slippage_bps: int = 500  # default 5%
    execute: bool = False  # False = simulation only


class SnipeResponse(BaseModel):
    """Response from surge sniper."""

    success: bool
    simulation: bool
    token_address: str
    estimated_cost: float
    estimated_output: float
    gas_estimate: int = 0
    tx_hash: str | None = None
    message: str = ""


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.1.0"
    uptime_seconds: float = 0.0


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
