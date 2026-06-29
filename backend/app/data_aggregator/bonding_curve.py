"""
BondingV5 curve math engine.

Implements the bonding curve pricing, progress calculation, and
graduation detection used by the Virtuals Protocol.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional


# ── Constants ─────────────────────────────────────────────────────────
# Virtuals Protocol bonding curve parameters (verify against deployment)

TOKEN_TOTAL_SUPPLY = 10_000_000  # 10M tokens per agent
VIRTUALS_PER_TOKEN = 1.0         # base rate (1 VIRTUAL per token at graduation)
# The curve typically uses a power law or exponential formula

# Default bonding curve exponent (adjust based on actual contract)
CURVE_EXPONENT = 2.0


class BondingCurveState:
    """Represents the current state of a bonding curve for a token."""

    def __init__(
        self,
        total_supply: int = TOKEN_TOTAL_SUPPLY,
        current_supply: int = 0,
        virtuals_accumulated: int = 0,
        virtuals_reserve: int = 0,
        is_graduated: bool = False,
    ) -> None:
        self.total_supply = total_supply
        self.current_supply = current_supply
        self.virtuals_accumulated = virtuals_accumulated
        self.virtuals_reserve = virtuals_reserve
        self.is_graduated = is_graduated

    @classmethod
    def from_onchain(cls, data: Dict[str, Any]) -> "BondingCurveState":
        """Construct from on-chain getCurveState return values."""
        return cls(
            total_supply=int(data.get("total_supply", TOKEN_TOTAL_SUPPLY)),
            current_supply=int(data.get("supply", 0)),
            virtuals_accumulated=int(data.get("virtuals_accumulated", 0)),
            virtuals_reserve=int(data.get("virtuals_reserve", 0)),
            is_graduated=bool(data.get("is_graduated", False)),
        )

    @property
    def progress_percent(self) -> float:
        """Percentage of total supply that has been minted (0-100)."""
        if self.total_supply <= 0:
            return 100.0
        return round((self.current_supply / self.total_supply) * 100.0, 4)

    @property
    def remaining_supply(self) -> int:
        return max(0, self.total_supply - self.current_supply)

    @property
    def progress_decimal(self) -> float:
        """Progress as a 0.0-1.0 decimal."""
        if self.total_supply <= 0:
            return 1.0
        return self.current_supply / self.total_supply

    # ── Pricing ─────────────────────────────────────────────────────────

    def calculate_price(self, amount: int = 1) -> float:
        """Calculate the price in VIRTUAL for buying `amount` tokens.

        Uses the bonding curve formula:
        price = integral of curve(x) dx from current_supply to current_supply + amount

        Simplified model (adjust based on actual curve):
        For a linear curve: price = (virtuals_total / total_supply) * amount
        For a power law:    price uses integral of x^n

        Default: constant price proportional to progress.
        """
        if self.is_graduated:
            return 0.0  # pricing handled by Uniswap pool after graduation

        if self.total_supply <= 0:
            return 0.0

        # Current price per token at current progress
        base_price = self._calculate_instant_price(1)

        # For small amounts, approximate with linear
        if amount <= 100:
            return base_price * amount

        # For larger amounts, integrate the curve
        return self._integrate_price(self.current_supply, self.current_supply + amount)

    def _calculate_instant_price(self, at_supply: Optional[int] = None) -> float:
        """Instant marginal price at a given supply level."""
        supply = at_supply or self.current_supply
        if supply <= 0:
            supply = 1
        # Price increases as supply increases (standard bonding curve)
        # Using power law: price ∝ (supply/total_supply)^n
        progress = supply / self.total_supply if self.total_supply > 0 else 1.0
        base_virtuals = self.virtuals_accumulated / self.total_supply if self.total_supply > 0 else 0
        return (base_virtuals * (progress ** CURVE_EXPONENT)) / supply if supply > 0 else 0.0

    def _integrate_price(self, from_supply: int, to_supply: int) -> float:
        """Numerical integration of price from from_supply to to_supply."""
        steps = 100
        step_size = (to_supply - from_supply) / steps if steps > 0 else 0
        total = 0.0
        for i in range(steps):
            mid = from_supply + (i + 0.5) * step_size
            price = self._calculate_instant_price(int(mid))
            total += price * step_size
        return total

    def estimate_graduation_time(self, daily_volume_virtual: float = 0.0) -> Optional[int]:
        """Estimate hours until graduation given daily VIRTUAL volume."""
        if daily_volume_virtual <= 0 or self.is_graduated:
            return None
        if self.virtuals_reserve <= 0:
            return None
        # Remaining VIRTUAL needed / daily volume * 24h
        remaining_virtuals = self.virtuals_reserve - self.virtuals_accumulated
        if remaining_virtuals <= 0:
            return 0
        hours = (remaining_virtuals / daily_volume_virtual) * 24
        return int(hours)

    # ── Bonding Value ───────────────────────────────────────────────────

    def bonding_value_virtual(self) -> int:
        """Total VIRTUAL accumulated on the curve."""
        return self.virtuals_accumulated

    def bonding_value_usd(self, price_per_virtual: float = 0.0) -> float:
        """USD value of VIRTUAL accumulated (requires oracle)."""
        return self.virtuals_accumulated * price_per_virtual

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_supply": self.total_supply,
            "current_supply": self.current_supply,
            "virtuals_accumulated": self.virtuals_accumulated,
            "virtuals_reserve": self.virtuals_reserve,
            "is_graduated": self.is_graduated,
            "progress_percent": self.progress_percent,
            "remaining_supply": self.remaining_supply,
        }

    @classmethod
    def default(cls) -> "BondingCurveState":
        return cls()
