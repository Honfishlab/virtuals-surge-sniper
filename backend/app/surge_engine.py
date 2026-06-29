"""Surge detection engine for Virtuals Protocol tokens.

Calculates a composite alpha score (0–100) from four dimensions:
  surge  35% – volume/activity spike
  bonding 25% – curve progression momentum
  usage  20% – active users & engagement
  market 10% – 24 h volume signal
  growth 10% – holder/social growth

Detects new surges when volume/multiplier exceeds configurable thresholds,
and emits structured ``SurgeAlert`` events.

Configurable thresholds via environment variables:
  SURGE_MULTIPLIER_THRESHOLD   = 2.0  (default)
  ALPHA_SCORE_THRESHOLD        = 60.0 (default)
  SURGE_COOLDOWN_SECONDS       = 300  (default, 5 min)
  VOLUME_WINDOW_HOURS          = 6    (default)
  VOLUME_CHANGE_THRESHOLD_PCT  = 50.0 (default)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.aggregator import TokenEnrichmentData
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Alert severity levels."""

    LOW = "LOW"
    WARNING = "WARNING"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"
    CRITICAL = "CRITICAL"


class AlertType(str, Enum):
    """Type of surge alert."""

    VOLUME_SPIKE = "VOLUME_SPIKE"
    PRICE_SURGE = "PRICE_SURGE"
    COMBINED = "COMBINED"
    BONDING_MOMENTUM = "BONDING_MOMENTUM"
    SOCIAL_SURGE = "SOCIAL_SURGE"


class AlphaScore(str, Enum):
    """Human-readable alpha score buckets."""

    WEAK = "WEAK"       # 0-25
    MODERATE = "MODERATE"  # 25-50
    STRONG = "STRONG"     # 50-75
    VERY_STRONG = "VERY_STRONG"  # 75-100


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SurgeConfig(BaseModel):
    """Configurable surge detection parameters.

    Read from env vars with fallback defaults.
    """

    surge_multiplier_threshold: float = 2.0
    alpha_score_threshold: float = 60.0
    cooldown_seconds: int = 300
    volume_window_hours: int = 6
    volume_change_threshold_pct: float = 50.0

    @classmethod
    def from_env(cls) -> "SurgeConfig":
        import os

        return cls(
            surge_multiplier_threshold=float(
                os.getenv("SURGE_MULTIPLIER_THRESHOLD", "2.0"),
            ),
            alpha_score_threshold=float(
                os.getenv("ALPHA_SCORE_THRESHOLD", "60.0"),
            ),
            cooldown_seconds=int(
                os.getenv("SURGE_COOLDOWN_SECONDS", "300"),
            ),
            volume_window_hours=int(
                os.getenv("VOLUME_WINDOW_HOURS", "6"),
            ),
            volume_change_threshold_pct=float(
                os.getenv("VOLUME_CHANGE_THRESHOLD_PCT", "50.0"),
            ),
        )


class SurgeAlert(BaseModel):
    """Structured alert emitted by surge detection."""

    token_address: str
    severity: Severity
    alert_type: AlertType
    score: float  # alpha score
    surge_multiplier: float
    volume_change_pct: float
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cooldown_until: Optional[datetime] = None


class AlphaScoreBreakdown(BaseModel):
    """Breakdown of alpha score into its components."""

    surge_component: float
    bonding_component: float
    usage_component: float
    market_component: float
    growth_component: float
    total: float

    def bucket(self) -> AlphaScore:
        if self.total < 25:
            return AlphaScore.WEAK
        elif self.total < 50:
            return AlphaScore.MODERATE
        elif self.total < 75:
            return AlphaScore.STRONG
        return AlphaScore.VERY_STRONG


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SurgeEngine:
    """Core surge detection engine.

    Usage::

        engine = SurgeEngine()
        alert = engine.detect_surge(token_enrichment)
        score = engine.calculate_alpha_score(
            surge_multiplier=2.5,
            bonding_progress=0.3,
            daily_active_users=100,
            volume_24h=50000,
        )
    """

    def __init__(self, config: Optional[SurgeConfig] = None) -> None:
        self.config = config or SurgeConfig()
        self._last_alert: dict[str, datetime] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_alpha_score(
        self,
        surge_multiplier: float = 1.0,
        bonding_progress: float = 0.0,
        daily_active_users: int = 0,
        volume_24h: float = 0.0,
    ) -> float:
        """Calculate alpha score (0–100) from raw metrics.

        Same formula as :py:meth:`app.aggregator.VirtualsDataAggregator.calculate_alpha_score`
        but with explicit params for testing and reuse.
        """
        # Surge: 1× → 0, 3× → 50, 6× → 100
        surge_score = min((surge_multiplier - 1.0) / 2.0 * 100.0, 100.0)
        surge_score = max(surge_score, 0.0)

        # Bonding: linear 0–100
        bonding_score = bonding_progress * 100.0

        # Usage: log-scaled
        if daily_active_users <= 0:
            usage_score = 0.0
        else:
            usage_score = min(
                math.log2(daily_active_users + 1) / 10.0 * 100.0, 100.0,
            )

        # Market: log10-scaled
        if volume_24h <= 0:
            market_score = 0.0
        else:
            market_score = min(
                math.log10(volume_24h + 1) / 6.0 * 100.0, 100.0,
            )

        # Growth placeholder
        growth_score = 50.0

        raw = (
            0.35 * surge_score
            + 0.25 * bonding_score
            + 0.20 * usage_score
            + 0.10 * market_score
            + 0.10 * growth_score
        )

        return round(min(max(raw, 0.0), 100.0), 2)

    def calculate_alpha_breakdown(
        self,
        surge_multiplier: float = 1.0,
        bonding_progress: float = 0.0,
        daily_active_users: int = 0,
        volume_24h: float = 0.0,
    ) -> AlphaScoreBreakdown:
        """Same as calculate_alpha_score but returns component breakdown."""
        surge_score = min(max((surge_multiplier - 1.0) / 2.0 * 100.0, 0.0), 100.0)
        bonding_score = bonding_progress * 100.0
        usage_score = (
            0.0
            if daily_active_users <= 0
            else min(math.log2(daily_active_users + 1) / 10.0 * 100.0, 100.0)
        )
        market_score = (
            0.0
            if volume_24h <= 0
            else min(math.log10(volume_24h + 1) / 6.0 * 100.0, 100.0)
        )
        growth_score = 50.0

        total = (
            0.35 * surge_score
            + 0.25 * bonding_score
            + 0.20 * usage_score
            + 0.10 * market_score
            + 0.10 * growth_score
        )

        return AlphaScoreBreakdown(
            surge_component=round(surge_score, 2),
            bonding_component=round(bonding_score, 2),
            usage_component=round(usage_score, 2),
            market_component=round(market_score, 2),
            growth_component=round(growth_score, 2),
            total=round(total, 2),
        )

    def detect_surge(
        self,
        token: TokenEnrichmentData,
    ) -> Optional[SurgeAlert]:
        """Check a single token against surge thresholds.

        Returns a :class:`SurgeAlert` if the token exceeds the configured
        threshold, or ``None`` if no surge is detected.

        Respects cooldown: if a surge alert was emitted within
        ``config.cooldown_seconds`` for this address, returns ``None``.
        """
        now = datetime.now(timezone.utc)

        # Check cooldown
        last_alert = self._last_alert.get(token.address)
        if last_alert is not None:
            elapsed = (now - last_alert).total_seconds()
            if elapsed < self.config.cooldown_seconds:
                return None

        # Calculate alpha score
        alpha = self.calculate_alpha_score(
            surge_multiplier=token.surge_multiplier,
            bonding_progress=token.bonding_state.get("progress", 0.0),
            daily_active_users=token.usage_data.get(
                "daily_active_users", 0,
            ),
            volume_24h=token.volume_24h,
        )

        # Check thresholds
        if alpha < self.config.alpha_score_threshold:
            return None

        # Determine severity and alert type
        severity = self._severity_for(alpha, token.surge_multiplier)
        alert_type = self._determine_alert_type(token)

        # Build cooldown_until
        cooldown_until = now.timestamp() + self.config.cooldown_seconds

        alert = SurgeAlert(
            token_address=token.address,
            severity=severity,
            alert_type=alert_type,
            score=round(alpha, 2),
            surge_multiplier=token.surge_multiplier,
            volume_change_pct=token.price_change_24h,  # proxy
            message=self._alert_message(severity, token),
        )

        # Track for cooldown
        self._last_alert[token.address] = now

        return alert

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _severity_for(
        self, alpha: float, surge_mult: float,
    ) -> Severity:
        if alpha >= 90 and surge_mult >= 5.0:
            return Severity.CRITICAL
        elif alpha >= 80 and surge_mult >= 3.0:
            return Severity.EMERGENCY
        elif alpha >= 70:
            return Severity.ALERT
        elif alpha >= self.config.alpha_score_threshold:
            return Severity.WARNING
        return Severity.LOW

    def _determine_alert_type(self, token: TokenEnrichmentData) -> AlertType:
        bonding_progress = token.bonding_state.get("progress", 0.0)
        if token.surge_multiplier >= 2.0 and bonding_progress > 0.5:
            return AlertType.COMBINED
        elif bonding_progress > 0.5:
            return AlertType.BONDING_MOMENTUM
        elif token.surge_multiplier >= 2.0:
            return AlertType.VOLUME_SPIKE
        elif token.price_change_24h > 10.0:
            return AlertType.PRICE_SURGE
        return AlertType.COMBINED

    def _alert_message(
        self, severity: Severity, token: TokenEnrichmentData,
    ) -> str:
        return (
            f"[{severity.value}] {token.symbol} ({token.address[:8]}…): "
            f"alpha={token.alpha_score:.1f}, "
            f"surge={token.surge_multiplier:.2f}x"
        )


# ---------------------------------------------------------------------------
# Volume surge calculator (standalone)
# ---------------------------------------------------------------------------


class VolumeSurgeCalculator:
    """Calculate surge multiplier from volume history arrays.

    Compares recent volume to historical baseline to detect abnormal spikes.
    """

    def __init__(self, window_size: int = 6) -> None:
        self.window_size = window_size

    def calculate_surge_multiplier(
        self, volumes: list[float], window: Optional[int] = None,
    ) -> float:
        """Calculate surge multiplier from a list of volume snapshots.

        Compares the last entry to the geometric mean of the previous N entries,
        weighted by a simple EMA to give more weight to recent baseline values.

        Args:
            volumes: List of volume values, indexed from oldest to newest.
            window: Number of recent samples to use as baseline (default: config).

        Returns:
            Multiplier > 1.0 indicates a surge.  == 1.0 means no surge.
        """
        if len(volumes) < 2:
            return 1.0

        w = window or self.window_size
        recent = volumes[-1]
        baseline = volumes[-(w + 1):-1] if len(volumes) > w else volumes[:-1]

        if not baseline or recent <= 0:
            return 1.0

        # Simple geometric mean for baseline (resistant to outliers)
        try:
            log_sum = sum(math.log(v) for v in baseline if v > 0)
            geo_mean = math.exp(log_sum / len(baseline))
        except (ValueError, OverflowError):
            geo_mean = sum(baseline) / len(baseline)

        if geo_mean <= 0:
            return 1.0

        multiplier = recent / geo_mean

        # Clamp: if multiplier < 1, treat as no surge
        return max(multiplier, 1.0)
