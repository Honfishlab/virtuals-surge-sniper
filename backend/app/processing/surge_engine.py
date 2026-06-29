"""
Surge detection engine.

Calculates surge multipliers, alpha scores, and detects new surge events.

Scoring:
- Surge score: weighted combo of volume spike + activity spike
- Alpha score: composite of surge + usage + bonding momentum + trend
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models import SurgeAlert, TokenData

logger = logging.getLogger(__name__)


class SurgeEngine:
    """Real-time surge detection and alpha scoring."""

    def __init__(
        self,
        surge_volume_multiplier: float | None = None,
        surge_activity_multiplier: float | None = None,
        alpha_weight_surge: float | None = None,
        alpha_weight_usage: float | None = None,
        alpha_weight_bonding: float | None = None,
        alpha_weight_trend: float | None = None,
    ) -> None:
        self.surge_volume_multiplier = surge_volume_multiplier or settings.surge_volume_multiplier
        self.surge_activity_multiplier = surge_activity_multiplier or settings.surge_activity_multiplier
        self.alpha_weight_surge = alpha_weight_surge or settings.alpha_weight_surge
        self.alpha_weight_usage = alpha_weight_usage or settings.alpha_weight_usage
        self.alpha_weight_bonding = alpha_weight_bonding or settings.alpha_weight_bonding
        self.alpha_weight_trend = alpha_weight_trend or settings.alpha_weight_trend

        # Historical baselines (in-memory, keyed by token address)
        self._volume_history: Dict[str, List[float]] = {}
        self._activity_history: Dict[str, List[float]] = {}
        self._price_history: Dict[str, List[float]] = {}

    # ── Score Calculations ──────────────────────────────────────────────

    def calculate_surge_score(self, token: TokenData) -> float:
        """Calculate surge multiplier (0-10 scale, >1 indicates surge).

        Combines volume spike and activity spike.
        """
        # Volume component: compare 24h volume to historical average
        volume_mult = self._calculate_volume_multiplier(token)

        # Activity component: compare ACP jobs to historical average
        activity_mult = self._calculate_activity_multiplier(token)

        # Combined surge score (0-10)
        raw_score = (volume_mult + activity_mult) / 2.0

        # Clamp to 0-10
        return min(10.0, max(0.0, round(raw_score, 2)))

    def _calculate_volume_multiplier(self, token: TokenData) -> float:
        """Volume surge multiplier.

        Compares current 24h volume to rolling average.
        Returns multiplier (e.g., 2.5 = 2.5x normal volume).
        """
        current_volume = token.price.volume_24h

        # Store historical data point
        if token.address not in self._volume_history:
            self._volume_history[token.address] = []
        self._volume_history[token.address].append(current_volume)

        # Keep only last 10 data points (~10 polling cycles)
        self._volume_history[token.address] = self._volume_history[token.address][-10:]

        if len(self._volume_history[token.address]) < 3:
            return 1.0  # Not enough history yet

        historical_avg = sum(self._volume_history[token.address][:-1]) / max(1, len(self._volume_history[token.address]) - 1)
        if historical_avg <= 0:
            return 1.0

        return current_volume / historical_avg

    def _calculate_activity_multiplier(self, token: TokenData) -> float:
        """Activity surge multiplier.

        Compares current ACP job count to historical average.
        """
        current_jobs = token.usage.acp_jobs_24h

        if token.address not in self._activity_history:
            self._activity_history[token.address] = []
        self._activity_history[token.address].append(current_jobs)
        self._activity_history[token.address] = self._activity_history[token.address][-10:]

        if len(self._activity_history[token.address]) < 3:
            return 1.0

        historical_avg = sum(self._activity_history[token.address][:-1]) / max(1, len(self._activity_history[token.address]) - 1)
        if historical_avg <= 0:
            return 1.0

        return current_jobs / historical_avg

    def calculate_alpha_score(self, token: TokenData) -> Dict[str, float]:
        """Calculate composite alpha score (0-100).

        Components:
        - Surge component (0-100): 35% weight
        - Usage component (0-100): 30% weight  
        - Bonding momentum component (0-100): 20% weight
        - Trend component (0-100): 15% weight
        """
        # Surge component (0-10 → 0-100)
        surge_raw = self.calculate_surge_score(token)
        surge_component = min(100.0, surge_raw * 10.0)

        # Usage component: normalize ACP jobs to 0-100 scale
        # 1000+ jobs/24h = 100 score
        usage_component = min(100.0, (token.usage.acp_jobs_24h / 1000.0) * 100.0)

        # Bonding component: progress toward graduation
        # Higher progress = more commitment, but still on curve = momentum
        bonding_raw = token.bonding.progress_percent if token.bonding.progress_percent > 0 else 50.0
        # Bonus for being between 30-80% (active accumulation phase)
        if 30 <= bonding_raw <= 80:
            bonding_component = 70.0 + (bonding_raw / 100.0) * 30.0
        else:
            bonding_component = bonding_raw

        # Trend component: price momentum
        if token.price.price_24h_ago > 0:
            price_change = (token.price.current_price - token.price.price_24h_ago) / token.price.price_24h_ago
            # Normalize: -50% to +200% → 0-100
            trend_component = min(100.0, max(0.0, (price_change + 0.5) * (100.0 / 2.5)))
        else:
            trend_component = 50.0

        # Weighted composite
        overall = (
            self.alpha_weight_surge * surge_component +
            self.alpha_weight_usage * usage_component +
            self.alpha_weight_bonding * bonding_component +
            self.alpha_weight_trend * trend_component
        )

        overall = round(min(100.0, max(0.0, overall)), 2)

        return {
            "overall_score": overall,
            "surge_component": round(surge_component, 2),
            "usage_component": round(usage_component, 2),
            "bonding_component": round(bonding_component, 2),
            "trend_component": round(trend_component, 2),
        }

    # ── Detection ───────────────────────────────────────────────────────

    def detect_surges(self, tokens: List[TokenData]) -> List[SurgeAlert]:
        """Scan all tokens for active surges.

        Returns list of SurgeAlert for tokens exceeding thresholds.
        """
        alerts: List[SurgeAlert] = []
        now = datetime.utcnow()

        for token in tokens:
            surge_score = self.calculate_surge_score(token)
            is_surging = surge_score > self.surge_volume_multiplier

            if is_surging:
                # Determine surge type
                vol_mult = self._calculate_volume_multiplier(token)
                act_mult = self._calculate_activity_multiplier(token)

                if vol_mult > act_mult * 1.2:
                    surge_type = "volume"
                    details = f"Volume {vol_mult:.1f}x normal"
                elif act_mult > vol_mult * 1.2:
                    surge_type = "activity"
                    details = f"Activity {act_mult:.1f}x normal"
                else:
                    surge_type = "combined"
                    details = f"Volume {vol_mult:.1f}x, Activity {act_mult:.1f}x"

                alerts.append(SurgeAlert(
                    token_address=token.address,
                    token_name=token.name,
                    surge_type=surge_type,
                    surge_score=round(surge_score, 2),
                    surge_multiplier=round(max(vol_mult, act_mult), 2),
                    timestamp=now,
                    details=details,
                ))

        # Sort by score descending
        alerts.sort(key=lambda a: a.surge_score, reverse=True)
        return alerts

    def calculate_token_alpha(self, token: TokenData) -> Dict[str, float]:
        """Calculate alpha score for a single token."""
        return self.calculate_alpha_score(token)

    # ── History Management ──────────────────────────────────────────────

    def prune_history(self, older_than_hours: int = 24) -> None:
        """Remove historical data older than specified hours (to save memory)."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        cutoff_ts = cutoff.timestamp()

        for key in list(self._volume_history.keys()):
            if len(self._volume_history[key]) > 20:
                self._volume_history[key] = self._volume_history[key][-20:]

        for key in list(self._activity_history.keys()):
            if len(self._activity_history[key]) > 20:
                self._activity_history[key] = self._activity_history[key][-20:]

    # ── Presets ─────────────────────────────────────────────────────────

    @classmethod
    def with_weights(cls, weights: Dict[str, float]) -> "SurgeEngine":
        """Create a SurgeEngine with custom scoring weights.

        Example:
            engine = SurgeEngine.with_weights({
                "surge": 0.4,
                "usage": 0.4,
                "bonding": 0.1,
                "trend": 0.1,
            })
        """
        return cls(
            surge_volume_multiplier=2.0,
            surge_activity_multiplier=1.5,
            alpha_weight_surge=weights.get("surge", 0.35),
            alpha_weight_usage=weights.get("usage", 0.30),
            alpha_weight_bonding=weights.get("bonding", 0.20),
            alpha_weight_trend=weights.get("trend", 0.15),
        )
