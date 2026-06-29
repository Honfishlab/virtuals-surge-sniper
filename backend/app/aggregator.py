"""VirtualsDataAggregator — unified data pipeline for Virtuals Protocol.

Integrates three data sources:
  1. ACP (Virtuals API) – token metadata, holder counts, social metrics
  2. Dune Analytics  – on-chain volume, transfer history, holder growth
  3. Base RPC        – direct on-chain state (bonding curve, token balance)

The aggregator enriches every token with usage, surge, bonding, and alpha
metrics, then exposes them through a clean async API.
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Any, Optional

import httpx

from app.bonding_curve import BondingCurve, CurveState
from app.cache.redis import CacheClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic-free dataclasses for performance
# ---------------------------------------------------------------------------


class TokenMetadata:
    """Basic token information from ACP / on-chain."""

    def __init__(
        self,
        address: str,
        name: str = "",
        symbol: str = "",
        decimals: int = 18,
        total_supply: int = 0,
    ) -> None:
        self.address = address
        self.name = name
        self.symbol = symbol
        self.decimals = decimals
        self.total_supply = total_supply


class UsageMetrics:
    """Usage / engagement metrics."""

    def __init__(
        self,
        daily_active_users: int = 0,
        transactions_24h: int = 0,
        unique_holders: int = 0,
        follower_count: int = 0,
        mention_count_24h: int = 0,
        volume_24h: float = 0.0,
    ) -> None:
        self.daily_active_users = daily_active_users
        self.transactions_24h = transactions_24h
        self.unique_holders = unique_holders
        self.follower_count = follower_count
        self.mention_count_24h = mention_count_24h
        self.volume_24h = volume_24h


class BondingMetrics:
    """Derived bonding-curve metrics."""

    def __init__(
        self,
        progress: float = 0.0,
        eth_raised: float = 0.0,
        eth_value_usd: float = 0.0,
        price_per_virtual_eth: float = 0.0,
        price_per_virtual_usd: float = 0.0,
        virtual_accumulated: int = 0,
        virtual_remaining: int = 0,
        is_graduated: bool = False,
        price_appreciation: float = 1.0,
    ) -> None:
        self.progress = progress
        self.eth_raised = eth_raised
        self.eth_value_usd = eth_value_usd
        self.price_per_virtual_eth = price_per_virtual_eth
        self.price_per_virtual_usd = price_per_virtual_usd
        self.virtual_accumulated = virtual_accumulated
        self.virtual_remaining = virtual_remaining
        self.is_graduated = is_graduated
        self.price_appreciation = price_appreciation


class SurgeMetrics:
    """Surge detection results."""

    def __init__(
        self,
        surge_multiplier: float = 1.0,
        volume_change_pct: float = 0.0,
        price_change_pct: float = 0.0,
        is_surge: bool = False,
    ) -> None:
        self.surge_multiplier = surge_multiplier
        self.volume_change_pct = volume_change_pct
        self.price_change_pct = price_change_pct
        self.is_surge = is_surge


class TokenEnrichmentData:
    """Complete enriched token data."""

    def __init__(
        self,
        address: str,
        name: str = "",
        symbol: str = "",
        surge_multiplier: float = 1.0,
        alpha_score: float = 0.0,
        bonding_state: Optional[dict[str, Any]] = None,
        usage_data: Optional[dict[str, Any]] = None,
        volume_24h: float = 0.0,
        price_change_24h: float = 0.0,
        holders: int = 0,
        followers: int = 0,
    ) -> None:
        self.address = address
        self.name = name
        self.symbol = symbol
        self.surge_multiplier = surge_multiplier
        self.alpha_score = alpha_score
        self.bonding_state = bonding_state or {}
        self.usage_data = usage_data or {}
        self.volume_24h = volume_24h
        self.price_change_24h = price_change_24h
        self.holders = holders
        self.followers = followers


class TokenDetail:
    """Detailed token view combining all sources."""

    def __init__(
        self,
        address: str,
        metadata: TokenMetadata,
        usage: UsageMetrics,
        bonding: BondingMetrics,
        surge: SurgeMetrics,
        alpha_score: float,
        enriched: TokenEnrichmentData,
    ) -> None:
        self.address = address
        self.metadata = metadata
        self.usage = usage
        self.bonding = bonding
        self.surge = surge
        self.alpha_score = alpha_score
        self.enriched = enriched


# ---------------------------------------------------------------------------
# Thin HTTP clients
# ---------------------------------------------------------------------------


class ACPClient:
    """Async wrapper for Virtuals ACP API  https://api.acp.virtuals.io"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.acp.virtuals.io",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._http: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            headers = (
                {"Authorization": f"Bearer {self.api_key}"}
                if self.api_key
                else {}
            )
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        return self._http

    async def get_tokens(self) -> list[dict[str, Any]]:
        client = await self._client()
        try:
            resp = await client.get("/v1/tokens")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            return data.get("tokens", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("ACP get_tokens failed: %s", exc)
            return []

    async def get_token_info(self, address: str) -> dict[str, Any]:
        client = await self._client()
        try:
            resp = await client.get(f"/v1/tokens/{address}")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ACP get_token_info failed for %s: %s", address, exc,
            )
            return {}

    async def get_usage_metrics(self, address: str) -> dict[str, Any]:
        client = await self._client()
        try:
            resp = await client.get(f"/v1/tokens/{address}/metrics")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ACP usage metrics failed for %s: %s", address, exc,
            )
            return {}

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


class DuneClient:
    """Async wrapper for Dune Analytics REST API.

    Docs: https://docs.dune.com/api-rest  •  Auth: X-Dune-API-Key header.
    """

    def __init__(
        self, api_key: str = "", base_url: str = "https://api.dune.com",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self._http: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-Dune-API-Key": self.api_key},
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._http

    async def get_volume_data(
        self, token_address: str, window_hours: int = 24,
    ) -> dict[str, Any]:
        query_id = "virtuals_protocol.token_volume"
        client = await self._client()
        try:
            resp = await client.get(
                f"/api/v1/query/{query_id}/results",
                params={"address": token_address, "hours": window_hours},
            )
            resp.raise_for_status()
            rows = (
                resp.json().get("result", {}).get("rows", [])
            )
            if rows:
                row = rows[0]
                return {
                    "volume_usd": row.get("volume_usd", 0),
                    "swap_count": row.get("swap_count", 0),
                    "window_hours": window_hours,
                }
            return {
                "volume_usd": 0.0,
                "swap_count": 0,
                "window_hours": window_hours,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Dune volume query failed for %s: %s",
                token_address, exc,
            )
            return {
                "volume_usd": 0.0,
                "swap_count": 0,
                "window_hours": window_hours,
            }

    async def get_holder_growth(
        self, token_address: str, days: int = 7,
    ) -> dict[str, Any]:
        client = await self._client()
        try:
            resp = await client.get(
                "/api/v1/query/virtuals_protocol.holders/results",
                params={"address": token_address, "days": days},
            )
            resp.raise_for_status()
            rows = resp.json().get("result", {}).get("rows", [])
            if rows:
                row = rows[0]
                return {
                    "current_holders": row.get("current_holders", 0),
                    "growth_pct": row.get("growth_pct", 0),
                }
            return {"current_holders": 0, "growth_pct": 0}
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Dune holder growth failed for %s: %s",
                token_address, exc,
            )
            return {"current_holders": 0, "growth_pct": 0}

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


class OnChainClient:
    """Base RPC client via raw JSON-RPC (works with eth_getStorageAt / eth_call).

    Connects to a Base mainnet RPC (Alchemy, Quicknode, etc.).
    """

    def __init__(self, rpc_url: str = "") -> None:
        self.rpc_url = rpc_url
        self._http: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.rpc_url,
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        return self._http

    async def _call(self, method: str, params: list[Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }
        client = await self._client()
        try:
            resp = await client.post("", json=payload)
            resp.raise_for_status()
            return resp.json().get("result")
        except Exception as exc:  # noqa: BLE001
            logger.warning("RPC call %s failed: %s", method, exc)
            return None

    async def get_bonding_state(self, contract_address: str) -> dict[str, Any]:
        """Return raw bonding-curve state.

        In production this would call eth_getStorageAt or eth_call with the
        BondingV5 ABI.  A placeholder implementation is provided so the rest
        of the pipeline compiles and type-checks correctly.
        """
        return {
            "eth_reserve": 0,
            "virtual_reserve": 0,
            "current_virtual_supply": 0,
            "total_virtual_supply": 0,
            "graduation_virtual_supply": 0,
            "fee_bps": 30,
            "address": contract_address,
        }

    async def get_eth_price_usd(self) -> float:
        """Fetch ETH/USD from CoinGecko as a fallback oracle."""
        try:
            client = await self._client()
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "ethereum", "vs_currencies": "usd"},
                timeout=5.0,
            )
            return float(
                resp.json().get("ethereum", {}).get("usd", 3000.0)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ETH price fetch failed: %s", exc)
            return 3000.0

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


# ---------------------------------------------------------------------------
# Bonding curve analyzer
# ---------------------------------------------------------------------------


class BondingCurveAnalyzer:
    """Derives BondingMetrics from raw curve state or from a BondingCurve."""

    @staticmethod
    def analyze_from_raw(
        eth_reserve: int,
        virtual_reserve: int,
        current_virtual_supply: int,
        total_virtual_supply: int,
        graduation_virtual_supply: int,
        fee_bps: int = 30,
        eth_price_usd: float = 3000.0,
        state: CurveState = CurveState.ACTIVE,
    ) -> BondingMetrics:
        """One-shot: build a BondingCurve and return metrics."""
        curve = BondingCurve.from_chain_state(
            eth_reserve=eth_reserve,
            virtual_reserve=virtual_reserve,
            current_virtual_supply=current_virtual_supply,
            total_virtual_supply=total_virtual_supply,
            graduation_virtual_supply=graduation_virtual_supply,
            fee_bps=fee_bps,
            eth_price_usd=eth_price_usd,
            state=state,
        )
        return BondingCurveAnalyzer.analyze(curve)

    @staticmethod
    def analyze(curve: BondingCurve) -> BondingMetrics:
        """Produce BondingMetrics from an existing BondingCurve instance."""
        price = curve.current_price()
        grad = curve.graduation_status()

        return BondingMetrics(
            progress=round(grad.progress, 6),
            eth_raised=round(curve.eth_raised(), 6),
            eth_value_usd=round(curve.eth_raised_usd(), 2),
            price_per_virtual_eth=round(price.price_per_virtual_eth, 18),
            price_per_virtual_usd=round(price.price_per_virtual_usd, 8),
            virtual_accumulated=curve.virtual_accumulated(),
            virtual_remaining=curve.virtual_remaining(),
            is_graduated=grad.is_graduated,
            price_appreciation=round(curve.price_appreciation(), 6),
        )


# ---------------------------------------------------------------------------
# Main aggregator
# ---------------------------------------------------------------------------


class VirtualsDataAggregator:
    """Core aggregation engine.

    Fetches from ACP, Dune, and on-chain sources in parallel, enriches
    tokens with all metrics, and optionally caches results in Redis.

    Usage::

        agg = VirtualsDataAggregator(
            acp_api_key="...",
            dune_api_key="...",
            base_rpc_url="https://base-mainnet.g.alchemy.com/v2/...",
            redis_url="redis://localhost:6379",
        )
        await agg.initialize()

        tokens = await agg.get_enriched_token_list()
        detail = await agg.get_token_details("0x...")
        score = VirtualsDataAggregator.calculate_alpha_score(...)
    """

    def __init__(
        self,
        acp_api_key: str = "",
        dune_api_key: str = "",
        base_rpc_url: str = "",
        redis_url: str = "redis://localhost:6379",
        cache_enabled: bool = True,
    ) -> None:
        self._acp = ACPClient(api_key=acp_api_key)
        self._dune = DuneClient(api_key=dune_api_key)
        self._onchain = OnChainClient(rpc_url=base_rpc_url)
        self._bonding_analyzer = BondingCurveAnalyzer()
        self._cache: Optional[CacheClient] = (
            CacheClient(url=redis_url)
            if cache_enabled
            else None
        )
        self._eth_price_usd: float = 3000.0

    # -- lifecycle ----------------------------------------------------------

    async def initialize(self) -> None:
        """Warm caches, resolve ETH price, verify connections."""
        if self._cache:
            await self._cache.connect()

        self._eth_price_usd = await self._onchain.get_eth_price_usd()

        logger.info(
            "Aggregator initialized — ETH price: $%.2f  cache: %s",
            self._eth_price_usd,
            "enabled" if self._cache else "disabled",
        )

    async def shutdown(self) -> None:
        """Close all HTTP connections and the Redis pool."""
        if self._cache:
            await self._cache.close()
        await self._acp.close()
        await self._dune.close()
        await self._onchain.close()

    # -- public API ---------------------------------------------------------

    async def get_enriched_token_list(
        self, limit: int = 50,
    ) -> list[TokenEnrichmentData]:
        """Return the full list of enriched tokens.

        1. Fetch token addresses from ACP.
        2. Fetch all metrics in parallel (bounded by *limit*).
        3. Cache the result and return.
        """
        # --- cache hit? ---
        if self._cache:
            cached = await self._cache.get_token_list()
            if cached:
                # Reconstruct from dicts
                results: list[dict[str, Any]] = cached if isinstance(cached, list) else []
                return [
                    TokenEnrichmentData(**item) for item in results  # type: ignore[arg-type]
                ]

        # --- fetch token list from ACP ---
        raw_tokens = await self._acp.get_tokens()
        addresses = [
            t.get("address", "") for t in raw_tokens
            if t.get("address")
        ][:limit]

        # --- parallel enrichment ---
        tasks = [self._enrich_single(address) for address in addresses]
        results = await asyncio.gather(*tasks)

        # Filter out exceptions (e.g. timeout)
        enriched: list[TokenEnrichmentData] = [
            r for r in results if isinstance(r, TokenEnrichmentData)
        ]

        # --- cache ---
        if self._cache:
            await self._cache.set_token_list(
                [t.__dict__ for t in enriched],
            )

        return enriched

    async def get_token_details(self, address: str) -> TokenDetail:
        """Return detailed enrichment for a single token address."""
        metadata_coro = self._fetch_metadata(address)
        usage_coro = self._fetch_usage(address)
        bonding_coro = self._fetch_bonding(address)
        surge_coro = self._fetch_surge_metrics(address)

        try:
            meta, usage, bonding, surge = await asyncio.gather(
                metadata_coro, usage_coro, bonding_coro, surge_coro,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Token detail fetch failed for %s: %s", address, exc)
            meta = {}
            usage = UsageMetrics()
            bonding = BondingMetrics()
            surge = SurgeMetrics()

        alpha = self.calculate_alpha_score(
            surge_multiplier=surge.surge_multiplier,
            bonding_progress=bonding.progress,
            daily_active_users=usage.daily_active_users,
            volume_24h=usage.volume_24h,
        )

        enriched = TokenEnrichmentData(
            address=address,
            name=meta.get("name", ""),
            symbol=meta.get("symbol", ""),
            surge_multiplier=surge.surge_multiplier,
            alpha_score=round(alpha, 2),
            bonding_state={
                "progress": bonding.progress,
                "eth_raised": bonding.eth_raised,
                "price_per_virtual_eth": bonding.price_per_virtual_eth,
            },
            usage_data={
                "daily_active_users": usage.daily_active_users,
                "transactions_24h": usage.transactions_24h,
                "volume_24h": usage.volume_24h,
            },
            volume_24h=usage.volume_24h,
            price_change_24h=surge.price_change_pct,
            holders=usage.unique_holders,
            followers=usage.follower_count,
        )

        metadata = TokenMetadata(
            address=meta.get("address", address),
            name=meta.get("name", ""),
            symbol=meta.get("symbol", ""),
        )

        detail = TokenDetail(
            address=address,
            metadata=metadata,
            usage=usage,
            bonding=bonding,
            surge=surge,
            alpha_score=alpha,
            enriched=enriched,
        )

        # cache
        if self._cache:
            await self._cache.set_token_detail(address, detail.__dict__)

        return detail

    # ------------------------------------------------------------------
    # Static helper
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_alpha_score(
        surge_multiplier: float = 1.0,
        bonding_progress: float = 0.0,
        daily_active_users: int = 0,
        volume_24h: float = 0.0,
    ) -> float:
        """Calculate alpha score (0–100).

        Weighted composite:
            surge 35%  – volume/activity spike
            bonding 25% – curve progression momentum
            usage  20%  – active users & engagement
            market 10%  – 24 h volume signal
            growth 10%  – holder/social growth
        """
        # Surge: 1× → 0, 3× → 50, 6× → 100
        surge_score = min((surge_multiplier - 1.0) / 2.0 * 100.0, 100.0)
        surge_score = max(surge_score, 0.0)

        # Bonding: linear 0–100
        bonding_score = bonding_progress * 100.0

        # Usage: log-scaled (≈ 0 for 0, ≈ 100 for 1024)
        if daily_active_users <= 0:
            usage_score = 0.0
        else:
            usage_score = min(
                math.log2(daily_active_users + 1) / 10.0 * 100.0, 100.0,
            )

        # Market: log10-scaled (≈ 0 for 0, ≈ 100 for 10^6)
        if volume_24h <= 0:
            market_score = 0.0
        else:
            market_score = min(
                math.log10(volume_24h + 1) / 6.0 * 100.0, 100.0,
            )

        # Growth placeholder (from Dune holder-growth data)
        growth_score = 50.0

        alpha = (
            0.35 * surge_score
            + 0.25 * bonding_score
            + 0.20 * usage_score
            + 0.10 * market_score
            + 0.10 * growth_score
        )

        return round(min(max(alpha, 0.0), 100.0), 2)

    # -- internal fetch helpers -------------------------------------------

    async def _enrich_single(
        self, address: str,
    ) -> TokenEnrichmentData:
        """Enrich a single token (used by get_enriched_token_list)."""
        try:
            meta, usage, bonding, surge = await asyncio.gather(
                self._fetch_metadata(address),
                self._fetch_usage(address),
                self._fetch_bonding(address),
                self._fetch_surge_metrics(address),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Enrichment failed for %s: %s", address, exc)
            return TokenEnrichmentData(address=address)

        alpha = self.calculate_alpha_score(
            surge_multiplier=surge.surge_multiplier,
            bonding_progress=bonding.progress,
            daily_active_users=usage.daily_active_users,
            volume_24h=usage.volume_24h,
        )

        return TokenEnrichmentData(
            address=address,
            name=meta.get("name", ""),
            symbol=meta.get("symbol", ""),
            surge_multiplier=surge.surge_multiplier,
            alpha_score=round(alpha, 2),
            bonding_state={
                "progress": bonding.progress,
                "eth_raised": bonding.eth_raised,
                "price_per_virtual_eth": bonding.price_per_virtual_eth,
            },
            usage_data={
                "daily_active_users": usage.daily_active_users,
                "transactions_24h": usage.transactions_24h,
                "volume_24h": usage.volume_24h,
            },
            volume_24h=usage.volume_24h,
            price_change_24h=surge.price_change_pct,
            holders=usage.unique_holders,
            followers=usage.follower_count,
        )

    async def _fetch_metadata(self, address: str) -> dict[str, Any]:
        data = await self._acp.get_token_info(address)
        if not data:
            return {"address": address, "name": "", "symbol": ""}
        return {
            "address": data.get("address", address),
            "name": data.get("name", ""),
            "symbol": data.get("symbol", ""),
            "decimals": data.get("decimals", 18),
            "total_supply": data.get("total_supply", 0),
        }

    async def _fetch_usage(self, address: str) -> UsageMetrics:
        usage = await self._acp.get_usage_metrics(address)

        volume_data = await self._dune.get_volume_data(address)

        return UsageMetrics(
            daily_active_users=usage.get("daily_active_users", 0),
            transactions_24h=usage.get("transactions_24h", 0),
            unique_holders=usage.get("unique_holders", 0),
            follower_count=usage.get("follower_count", 0),
            mention_count_24h=usage.get("mention_count_24h", 0),
            volume_24h=volume_data.get("volume_usd", 0.0),
        )

    async def _fetch_bonding(self, address: str) -> BondingMetrics:
        raw = await self._onchain.get_bonding_state(address)

        # If no on-chain data, return defaults
        if raw.get("eth_reserve", 0) == 0 and raw.get("virtual_reserve", 0) == 0:
            return BondingMetrics()

        return BondingCurveAnalyzer.analyze_from_raw(
            eth_reserve=raw.get("eth_reserve", 0),
            virtual_reserve=raw.get("virtual_reserve", 0),
            current_virtual_supply=raw.get("current_virtual_supply", 0),
            total_virtual_supply=raw.get("total_virtual_supply", 0),
            graduation_virtual_supply=raw.get("graduation_virtual_supply", 0),
            fee_bps=raw.get("fee_bps", 30),
            eth_price_usd=self._eth_price_usd,
        )

    async def _fetch_surge_metrics(self, address: str) -> SurgeMetrics:
        """Compare last-24 h volume vs prior-24 h volume."""
        current = await self._dune.get_volume_data(address, window_hours=24)
        previous = await self._dune.get_volume_data(address, window_hours=48)

        cur_vol = current.get("volume_usd", 0.0)
        prev_vol = previous.get("volume_usd", 0.0)

        volume_change_pct = (
            ((cur_vol - prev_vol) / prev_vol * 100.0)
            if prev_vol > 0
            else (0.0 if cur_vol == 0 else 100.0)
        )

        surge_multiplier = (
            cur_vol / prev_vol if prev_vol > 0 else (2.0 if cur_vol > 0 else 1.0)
        )

        return SurgeMetrics(
            surge_multiplier=round(max(surge_multiplier, 1.0), 4),
            volume_change_pct=round(volume_change_pct, 2),
            price_change_pct=0.0,  # wired from price oracle in production
            is_surge=surge_multiplier >= 2.0 and volume_change_pct > 50.0,
        )
