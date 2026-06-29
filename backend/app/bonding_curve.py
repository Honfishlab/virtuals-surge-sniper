"""Bonding curve math implementation for Virtuals Protocol BondingV5.

The BondingV5 curve uses a constant-product formula where:
  invariant = eth_reserve * virtual_reserve

Buying: user pays ETH (minus fee) and receives VIRTUAL tokens.
Selling: user returns VIRTUAL tokens and receives ETH (minus fee).

Progress towards graduation tracks how much of the VIRTUAL supply has been
sold.  Once graduation_threshold is reached, the liquidity is migrated to
Uniswap V2 and the curve enters the "graduated" state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CurveState(Enum):
    """Lifecycle state of a bonding curve."""

    ACTIVE = "active"
    GRADUATED = "graduated"
    MIGRATING = "migrating"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CurveStateData:
    """Raw on-chain state of a BondingV5 curve."""

    eth_reserve: int = 0  # Wei
    virtual_reserve: int = 0
    current_virtual_supply: int = 0
    total_virtual_supply: int = 0
    graduation_virtual_supply: int = 0
    fee_bps: int = 30  # default 0.3 %
    eth_price_usd: float = 0.0  # optional oracle price


@dataclass
class GraduatedStateData:
    """State after the curve has graduated to Uniswap."""

    lp_token_address: str = ""
    eth_pool_reserve: int = 0  # Wei
    virtual_pool_reserve: int = 0
    lp_total_supply: int = 0
    eth_price_usd: float = 0.0


@dataclass
class PriceSnapshot:
    """Price at a point in time."""

    price_per_virtual_eth: float
    price_per_virtual_usd: float
    eth_reserve: int
    virtual_reserve: int


@dataclass
class BuyQuote:
    """Result of a buy (amount_in ETH → amount_out VIRTUAL)."""

    amount_in_eth: int  # Wei
    amount_out_virtual: int
    price_impact_bps: float  # basis points
    effective_price_eth: float


@dataclass
class SellQuote:
    """Result of a sell (amount_in VIRTUAL → amount_out ETH)."""

    amount_in_virtual: int
    amount_out_eth: int  # Wei
    price_impact_bps: float
    effective_price_eth: float


@dataclass
class GraduationStatus:
    """Whether a curve has graduated (or is near graduation)."""

    progress: float  # 0.0 – 1.0
    is_graduated: bool
    virtuals_remaining: int
    eth_value_at_graduation: Optional[float] = None  # USD


# ---------------------------------------------------------------------------
# Core maths helpers
# ---------------------------------------------------------------------------

_USD_DECIMALS = 18
_ETH_DECIMALS = 18


def _safe_sqrt(x: int) -> int:
    """Integer square-root (floor)."""
    if x < 0:
        raise ValueError("sqrt of negative number")
    if x == 0:
        return 0
    return int(math.isqrt(x))


def _usd_from_wei(wei: int, eth_price_usd: float) -> float:
    """Convert Wei to USD using an external ETH price."""
    return (wei / 10 ** _ETH_DECIMALS) * eth_price_usd


def _virtual_price_from_reserves(
    eth_reserve: int,
    virtual_reserve: int,
    eth_price_usd: float = 0.0,
) -> PriceSnapshot:
    """Compute the current per-VIRTUAL price from on-chain reserves."""
    if virtual_reserve <= 0:
        raise ZeroDivisionError("virtual_reserve must be > 0")

    price_eth = eth_reserve / virtual_reserve
    price_usd = price_eth * eth_price_usd if eth_price_usd > 0 else 0.0

    return PriceSnapshot(
        price_per_virtual_eth=price_eth,
        price_per_virtual_usd=price_usd,
        eth_reserve=eth_reserve,
        virtual_reserve=virtual_reserve,
    )


# ---------------------------------------------------------------------------
# Bonding curve engine
# ---------------------------------------------------------------------------

class BondingCurve:
    """Encapsulates BondingV5 curve mathematics.

    Example usage
    -------------
    >>> curve = BondingCurve.from_chain_state(
    ...     eth_reserve=1000 * 10**18,
    ...     virtual_reserve=1_000_000 * 10**18,
    ...     current_virtual_supply=200_000 * 10**18,
    ...     total_virtual_supply=10_000_000 * 10**18,
    ...     graduation_virtual_supply=10_000_000 * 10**18,
    ...     eth_price_usd=3000.0,
    ... )
    >>> snap = curve.current_price()
    >>> quote = curve.buy_quote(eth_amount_in=1 * 10**18)  # 1 ETH
    """

    def __init__(
        self,
        eth_reserve: int,
        virtual_reserve: int,
        current_virtual_supply: int,
        total_virtual_supply: int,
        graduation_virtual_supply: int,
        fee_bps: int = 30,
        eth_price_usd: float = 0.0,
        state: CurveState = CurveState.ACTIVE,
    ) -> None:
        self.eth_reserve = eth_reserve
        self.virtual_reserve = virtual_reserve
        self.current_virtual_supply = current_virtual_supply
        self.total_virtual_supply = total_virtual_supply
        self.graduation_virtual_supply = graduation_virtual_supply
        self.fee_bps = fee_bps
        self.eth_price_usd = eth_price_usd
        self.state = state

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_chain_state(
        cls,
        eth_reserve: int,
        virtual_reserve: int,
        current_virtual_supply: int,
        total_virtual_supply: int,
        graduation_virtual_supply: int,
        fee_bps: int = 30,
        eth_price_usd: float = 0.0,
        state: CurveState = CurveState.ACTIVE,
    ) -> BondingCurve:
        return cls(
            eth_reserve=eth_reserve,
            virtual_reserve=virtual_reserve,
            current_virtual_supply=current_virtual_supply,
            total_virtual_supply=total_virtual_supply,
            graduation_virtual_supply=graduation_virtual_supply,
            fee_bps=fee_bps,
            eth_price_usd=eth_price_usd,
            state=state,
        )

    # ------------------------------------------------------------------
    # Current price
    # ------------------------------------------------------------------

    def current_price(self) -> PriceSnapshot:
        """Return the instantaneous price per VIRTUAL token."""
        return _virtual_price_from_reserves(
            self.eth_reserve, self.virtual_reserve, self.eth_price_usd
        )

    def cumulative_price(self) -> PriceSnapshot:
        """Price based on cumulative supply (total vs total_virtual_supply).

        This is the price a buyer would get at the very beginning of the
        curve — useful for measuring price appreciation.
        """
        # Virtuals Protocol pricing: initial price = total_eth_raised / total_virtual_supply
        # We use the current eth_reserve as a proxy for total ETH raised so far.
        initial_virtual_supply = self.graduation_virtual_supply
        if initial_virtual_supply <= 0:
            raise ZeroDivisionError("graduation_virtual_supply must be > 0")

        # The effective "initial" ETH reserve is scaled:
        #   at 0 virtual sold, eth_reserve should equal the initial pool size
        #   but we approximate using current reserves
        initial_eth = (
            self.eth_reserve
            * self.graduation_virtual_supply
            // self.current_virtual_supply
            if self.current_virtual_supply > 0
            else self.eth_reserve
        )

        return _virtual_price_from_reserves(
            initial_eth, self.graduation_virtual_supply, self.eth_price_usd
        )

    # ------------------------------------------------------------------
    # Quotes
    # ------------------------------------------------------------------

    def buy_quote(self, eth_amount_in: int) -> BuyQuote:
        """Calculate how many VIRTUAL tokens a buyer receives for *eth_amount_in* ETH.

        Uses the constant-product invariant:
            invariant = eth_reserve * virtual_reserve

        After the buy:
            new_eth_reserve = eth_reserve + eth_amount_in * (1 - fee_bps / 10000)
            new_virtual_reserve = invariant / new_eth_reserve
            amount_out = virtual_reserve - new_virtual_reserve
        """
        if eth_amount_in <= 0:
            raise ValueError("eth_amount_in must be > 0")
        if self.state != CurveState.ACTIVE:
            raise RuntimeError("Cannot buy from a non-active curve")

        # Fee-adjusted ETH contribution
        fee_multiplier = (10000 - self.fee_bps) / 10000
        eth_contribution = int(eth_amount_in * fee_multiplier)

        # Constant product
        invariant = self.eth_reserve * self.virtual_reserve
        new_eth_reserve = self.eth_reserve + eth_contribution
        new_virtual_reserve = invariant // new_eth_reserve

        amount_out_virtual = self.virtual_reserve - new_virtual_reserve
        if amount_out_virtual <= 0:
            return BuyQuote(
                amount_in_eth=eth_amount_in,
                amount_out_virtual=0,
                price_impact_bps=0.0,
                effective_price_eth=0.0,
            )

        # Price impact: (effective_price - spot_price) / spot_price
        spot_price = self.eth_reserve / self.virtual_reserve if self.virtual_reserve else 0
        effective_price = eth_amount_in / amount_out_virtual
        price_impact_bps = (
            ((effective_price - spot_price) / spot_price * 10000)
            if spot_price > 0
            else 0.0
        )

        return BuyQuote(
            amount_in_eth=eth_amount_in,
            amount_out_virtual=amount_out_virtual,
            price_impact_bps=round(price_impact_bps, 4),
            effective_price_eth=round(effective_price, 18),
        )

    def sell_quote(self, virtual_amount_in: int) -> SellQuote:
        """Calculate how much ETH a seller receives for *virtual_amount_in* VIRTUAL.

        After the sell:
            new_virtual_reserve = virtual_reserve + virtual_amount_in
            new_eth_reserve = invariant / new_virtual_reserve
            amount_out = eth_reserve - new_eth_reserve
        """
        if virtual_amount_in <= 0:
            raise ValueError("virtual_amount_in must be > 0")
        if self.state != CurveState.ACTIVE:
            raise RuntimeError("Cannot sell from a non-active curve")

        fee_multiplier = (10000 - self.fee_bps) / 10000

        new_virtual_reserve = self.virtual_reserve + virtual_amount_in
        invariant = self.eth_reserve * self.virtual_reserve
        new_eth_reserve = invariant // new_virtual_reserve

        raw_eth_out = self.eth_reserve - new_eth_reserve
        eth_out = int(raw_eth_out * fee_multiplier)

        # Price impact
        spot_price = self.eth_reserve / self.virtual_reserve if self.virtual_reserve else 0
        effective_price = eth_out / virtual_amount_in if virtual_amount_in else 0
        price_impact_bps = (
            ((spot_price - effective_price) / spot_price * 10000)
            if spot_price > 0
            else 0.0
        )

        return SellQuote(
            amount_in_virtual=virtual_amount_in,
            amount_out_eth=eth_out,
            price_impact_bps=round(price_impact_bps, 4),
            effective_price_eth=round(effective_price, 18),
        )

    # ------------------------------------------------------------------
    # Graduation
    # ------------------------------------------------------------------

    def graduation_status(self) -> GraduationStatus:
        """Return the progress towards graduation."""
        if self.state == CurveState.GRADUATED:
            return GraduationStatus(
                progress=1.0,
                is_graduated=True,
                virtuals_remaining=0,
                eth_value_at_graduation=_usd_from_wei(
                    self.eth_reserve, self.eth_price_usd
                )
                if self.eth_price_usd > 0
                else None,
            )

        progress = (
            self.current_virtual_supply / self.graduation_virtual_supply
            if self.graduation_virtual_supply > 0
            else 0.0
        )
        progress = min(progress, 1.0)

        remaining = self.graduation_virtual_supply - self.current_virtual_supply

        # Project ETH value at graduation (linear interpolation of ETH reserve)
        eth_value = None
        if self.eth_price_usd > 0 and progress > 0:
            # Current ETH value scaled to graduation size
            eth_value_at_current = _usd_from_wei(
                self.eth_reserve, self.eth_price_usd
            )
            # Rough projection: scale by graduation progress
            eth_value_at_graduation = eth_value_at_current / progress if progress > 0 else 0
            eth_value = eth_value_at_graduation

        return GraduationStatus(
            progress=round(progress, 6),
            is_graduated=progress >= 1.0,
            virtuals_remaining=max(remaining, 0),
            eth_value_at_graduation=eth_value,
        )

    # ------------------------------------------------------------------
    # Momentum / derived metrics
    # ------------------------------------------------------------------

    def virtual_accumulated(self) -> int:
        """Total VIRTUAL tokens that have accumulated (sold)."""
        return self.current_virtual_supply

    def virtual_remaining(self) -> int:
        """VIRTUAL tokens still on the curve."""
        return max(
            self.graduation_virtual_supply - self.current_virtual_supply, 0
        )

    def eth_raised(self) -> float:
        """Total ETH raised, in ETH units."""
        return self.eth_reserve / 10 ** _ETH_DECIMALS

    def eth_raised_usd(self) -> float:
        """Total ETH raised in USD."""
        return _usd_from_wei(self.eth_reserve, self.eth_price_usd)

    def market_cap_virtual(self) -> float:
        """Implied market cap in VIRTUAL tokens outstanding (not sold)."""
        price = self.current_price().price_per_virtual_eth
        remaining = self.virtual_remaining()
        return remaining * price

    def price_appreciation(self) -> float:
        """Ratio of current price vs initial (lowest) price.

        The initial price is approximated from the curve's graduation supply:
            initial_price ≈ eth_raised / graduation_virtual_supply
        Current price is eth_reserve / virtual_reserve (which shrinks as virtuals
        sell out, so price goes up).
        """
        try:
            if self.graduation_virtual_supply <= 0 or self.virtual_reserve <= 0:
                return 1.0

            current_price = self.current_price().price_per_virtual_eth
            # initial_price: if we scale eth_reserve to what it would be at
            # t=0 by dividing out the fraction already sold:
            fraction_sold = (
                self.current_virtual_supply / self.graduation_virtual_supply
                if self.graduation_virtual_supply > 0
                else 0.0
            )
            if fraction_sold <= 0:
                return 1.0
            # At t=0, eth_reserve was roughly current / fraction_sold
            # because current reserve = initial_reserve * fraction_sold
            initial_eth_for_price = self.eth_reserve / fraction_sold
            initial_price = initial_eth_for_price / self.graduation_virtual_supply

            if initial_price <= 0:
                return 1.0

            ratio = current_price / initial_price
            if math.isinf(ratio) or math.isnan(ratio):
                return 1.0
            return max(ratio, 1.0)  # never less than 1.0 on a healthy curve
        except (ZeroDivisionError, ValueError):
            return 1.0


# ---------------------------------------------------------------------------
# Graduated (Uniswap) state
# ---------------------------------------------------------------------------

class GraduatedPool:
    """Represents the post-graduation Uniswap V2-style pool."""

    def __init__(
        self,
        eth_reserve: int,
        virtual_reserve: int,
        lp_total_supply: int,
        eth_price_usd: float = 0.0,
        lp_token_address: str = "",
    ) -> None:
        self.eth_reserve = eth_reserve
        self.virtual_reserve = virtual_reserve
        self.lp_total_supply = lp_total_supply
        self.eth_price_usd = eth_price_usd
        self.lp_token_address = lp_token_address

    def current_price(self) -> PriceSnapshot:
        return _virtual_price_from_reserves(
            self.eth_reserve, self.virtual_reserve, self.eth_price_usd
        )

    def buy_quote(self, eth_amount_in: int) -> BuyQuote:
        """Uniswap V2 constant-product buy."""
        if eth_amount_in <= 0:
            raise ValueError("eth_amount_in must be > 0")

        fee_bps = 3  # Uniswap V2 fee
        fee_multiplier = (10000 - fee_bps) / 10000
        eth_contribution = int(eth_amount_in * fee_multiplier)

        invariant = self.eth_reserve * self.virtual_reserve
        new_eth_reserve = self.eth_reserve + eth_contribution
        new_virtual_reserve = invariant // new_eth_reserve

        amount_out = self.virtual_reserve - new_virtual_reserve

        spot_price = self.eth_reserve / self.virtual_reserve if self.virtual_reserve else 0
        effective_price = eth_amount_in / amount_out if amount_out > 0 else 0
        price_impact_bps = (
            ((effective_price - spot_price) / spot_price * 10000)
            if spot_price > 0
            else 0.0
        )

        return BuyQuote(
            amount_in_eth=eth_amount_in,
            amount_out_virtual=amount_out,
            price_impact_bps=round(price_impact_bps, 4),
            effective_price_eth=round(effective_price, 18),
        )

    def total_value_locked(self) -> float:
        """TVL in USD."""
        eth_value = _usd_from_wei(self.eth_reserve, self.eth_price_usd)
        virtual_value = _usd_from_wei(
            self.virtual_reserve * 0, self.eth_price_usd
        )  # We need VIRTUAL price from external source
        return eth_value * 2  # Rough: TVL ≈ 2 * ETH value
