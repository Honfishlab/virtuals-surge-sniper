"""Shared types and constants for Virtuals Surge Sniper."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TokenType(str, Enum):
    ON_CURVE = "on_curve"
    GRADUATED = "graduated"


class TokenStatus(str, Enum):
    ACTIVE = "active"
    SLEEPING = "sleeping"


class AgentConfig(BaseModel):
    """Configuration for a Virtuals Protocol agent."""

    name: str
    description: str
    creator: str
    model: str
    parameters: Optional[Dict[str, Any]] = {}
    is_verified: bool = False


class TokenData(BaseModel):
    """Complete token data with all metrics."""

    address: str
    name: str
    symbol: str
    agent_id: str
    creator: str
    description: str
    age_days: float
    launched_at: Optional[str] = None

    bonding: Dict[str, Any]
    price: Dict[str, Any]
    surge: Dict[str, Any]
    usage: Dict[str, Any]
    alpha_score: Dict[str, Any]

    accumulated_virtual: float = 0.0
    token_type: TokenType = TokenType.ON_CURVE
    status: TokenStatus = TokenStatus.ACTIVE

    class Config:
        json_schema_extra = {
            "example": {
                "address": "0x" + "a" * 39 + "1",
                "name": "NeuralChat",
                "symbol": "NCHAT",
                "agent_id": "agent_neural_chat",
                "creator": "0x" + "b" * 39 + "1",
                "description": "AI assistant for complex reasoning tasks",
                "age_days": 5.0,
                "bonding": {"progress_percent": 72.5},
                "price": {"market_cap": 22500, "current_price": 0.0045},
                "surge": {"is_surging": True, "volume_multiplier": 3.2},
                "usage": {"acp_jobs_24h": 1200},
                "alpha_score": {"overall_score": 87.5},
            }
        }
