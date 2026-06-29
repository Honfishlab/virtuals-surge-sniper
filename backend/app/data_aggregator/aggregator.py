"""
Main data aggregator - combines ACP, Dune, on-chain, and bonding curve data.

Produces enriched token data with all metrics needed by the dashboard.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from app.cache.redis import CacheClient, TTL_TOKEN_LIST, TTL_TOKEN_DETAIL
from app.config import settings
from app.data_aggregator.acp_client import ACPClient
from app.data_aggregator.bonding_curve import BondingCurveState
from app.data_aggregator.dune_client import DuneClient
from app.data_aggregator.onchain_client import OnChainClient
from app.models import TokenType, TokenData, TokenListItem, AlphaScoreResult
from app.processing.surge_engine import SurgeEngine

logger = logging.getLogger(__name__)


class VirtualsDataAggregator:
    """Unified data aggregator combining all Virtuals Protocol data sources."""

    def __init__(
        self,
        cache: CacheClient | None = None,
        acp_client: ACPClient | None = None,
        dune_client: DuneClient | None = None,
        onchain_client: OnChainClient | None = None,
        surge_engine: SurgeEngine | None = None,
    ) -> None:
        self.cache = cache or CacheClient(settings.redis_url)
        self.acp = acp_client or ACPClient(settings.acp_auth_token)
        self.dune = dune_client or DuneClient(settings.dune_api_key)
        self.onchain = onchain_client or OnChainClient(settings.base_rpc_url)
        self.surge_engine = surge_engine or SurgeEngine()

        # Known tokens (address -> TokenData)
        self._tokens: Dict[str, TokenData] = {}
        self._initialized = False

    # -- Initialization --

    async def initialize(self) -> None:
        """Connect to all data sources."""
        await self.cache.connect()

        if self.acp.is_configured:
            logger.info("ACP client initialized with token")
        else:
            logger.warning("ACP client not configured - using on-chain fallback")

        if self.dune.is_configured:
            logger.info("Dune client initialized")
        else:
            logger.warning("Dune client not configured - some features disabled")

        if self.onchain.connected:
            logger.info("On-chain client connected to %s", settings.base_rpc_url)
        else:
            logger.warning("On-chain client not connected")

        self._initialized = True

    # -- Primary: Enriched Token List --

    async def get_enriched_token_list(self) -> List[TokenData]:
        """Get full list of tokens with all metrics."""
        cached = await self.cache.get(CacheClient.token_list_key())
        if cached is not None:
            logger.debug("Token list served from cache")
            return [TokenData(**t) if isinstance(t, dict) else t for t in cached]

        tokens = await self._discover_tokens()
        if not tokens:
            logger.warning("No tokens discovered - returning empty list")
            return []

        enrichment_tasks = [self._enrich_single_token(t) for t in tokens]
        enriched = await asyncio.gather(*enrichment_tasks, return_exceptions=True)

        result: List[TokenData] = []
        for item in enriched:
            if isinstance(item, Exception):
                logger.error("Enrichment failed: %s", item)
            elif isinstance(item, TokenData):
                result.append(item)
                self._tokens[item.address] = item

        if result:
            data = [t.model_dump() for t in result]
            await self.cache.set(CacheClient.token_list_key(), data, TTL_TOKEN_LIST)

        return result

    async def _discover_tokens(self) -> List[Dict[str, Any]]:
        """Discover tokens from on-chain and ACP sources."""
        tasks: List = []

        if self.onchain.connected:
            tasks.append(self._discover_from_chain())

        if self.acp.is_configured:
            tasks.append(self._discover_from_acp())

        if not tasks:
            return await self._get_fallback_tokens()

        results = await asyncio.gather(*tasks, return_exceptions=True)
        tokens: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        for result in results:
            if isinstance(result, Exception):
                logger.error("Token discovery failed: %s", result)
                continue
            if isinstance(result, list):
                for t in result:
                    addr = t.get("address", "")
                    if addr and addr not in seen:
                        seen.add(addr)
                        tokens.append(t)

        return tokens

    async def _discover_from_chain(self) -> List[Dict[str, Any]]:
        """Discover tokens from on-chain TokenCreated events."""
        try:
            events = self.onchain.get_token_created_events(limit=50)
            tokens = []
            now = datetime.now(timezone.utc)
            for event in events:
                tokens.append({
                    "address": event["token"],
                    "name": event.get("token", "")[:30],
                    "symbol": "",
                    "agent_id": event.get("agent", ""),
                    "launched_at": datetime.fromtimestamp(event["timestamp"], tz=timezone.utc),
                    "age_days": (now - datetime.fromtimestamp(event["timestamp"], tz=timezone.utc)).days,
                })
            return tokens
        except Exception as exc:
            logger.error("_discover_from_chain error: %s", exc)
            return []

    async def _discover_from_acp(self) -> List[Dict[str, Any]]:
        """Discover tokens from ACP agent listing."""
        try:
            agents = await self.acp.list_agents(limit=100, sort_by="trending")
            tokens = []
            for agent in agents:
                tokens.append({
                    "address": agent.get("address", agent.get("token_address", "")),
                    "name": agent.get("name", agent.get("title", "")),
                    "symbol": agent.get("symbol", ""),
                    "agent_id": agent.get("id", agent.get("agent_id", "")),
                    "creator": agent.get("creator", ""),
                    "launched_at": agent.get("created_at"),
                    "age_days": 0,
                })
            return tokens
        except Exception as exc:
            logger.error("_discover_from_acp error: %s", exc)
            return []

    async def _get_fallback_tokens(self) -> List[Dict[str, Any]]:
        """Fallback: demo tokens for development."""
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        return [
            {
                "address": "0x" + "a" * 39 + "1",
                "name": "NeuralChat",
                "symbol": "NCHAT",
                "agent_id": "agent_neural_chat",
                "creator": "0x" + "b" * 39 + "1",
                "description": "AI assistant for complex reasoning tasks",
                "launched_at": now - timedelta(days=5),
                "age_days": 5.0,
            },
            {
                "address": "0x" + "a" * 39 + "2",
                "name": "CodeGen AI",
                "symbol": "CGEN",
                "agent_id": "agent_code_gen",
                "creator": "0x" + "b" * 39 + "2",
                "description": "Automated code generation and review",
                "launched_at": now - timedelta(days=12),
                "age_days": 12.0,
            },
            {
                "address": "0x" + "a" * 39 + "3",
                "name": "DataInsight",
                "symbol": "DSIGHT",
                "agent_id": "agent_data_insight",
                "creator": "0x" + "b" * 39 + "3",
                "description": "Data analysis and visualization agent",
                "launched_at": now - timedelta(hours=18),
                "age_days": 0.75,
            },
            {
                "address": "0x" + "a" * 39 + "4",
                "name": "GameBot Pro",
                "symbol": "GBOT",
                "agent_id": "agent_gamebot",
                "creator": "0x" + "b" * 39 + "4",
                "description": "Gaming assistant with multi-game support",
                "launched_at": now - timedelta(days=30),
                "age_days": 30.0,
            },
            {
                "address": "0x" + "a" * 39 + "5",
                "name": "MusicVerse",
                "symbol": "MVERSE",
                "agent_id": "agent_music",
                "creator": "0x" + "b" * 39 + "5",
                "description": "AI music generation and composition",
                "launched_at": now - timedelta(days=2),
                "age_days": 2.0,
            },
            {
                "address": "0x" + "a" * 39 + "6",
                "name": "FinanceWiz",
                "symbol": "FWIZ",
                "agent_id": "agent_finance",
                "creator": "0x" + "b" * 39 + "6",
                "description": "Financial analysis and portfolio tracking",
                "launched_at": now - timedelta(days=20),
                "age_days": 20.0,
            },
        ]

    # -- Token Enrichment --

    async def _enrich_single_token(self, token_info: Dict[str, Any]) -> TokenData:
        """Enrich a single token with all metrics."""
        address = token_info.get("address", "")

        token = TokenData(
            address=address,
            name=token_info.get("name", "Unknown"),
            symbol=token_info.get("symbol", ""),
            agent_id=token_info.get("agent_id", ""),
            creator=token_info.get("creator", ""),
            age_days=token_info.get("age_days", 0),
            launched_at=token_info.get("launched_at"),
        )

        # Parallel enrichment tasks
        tasks: Dict[str, Any] = {}

        if address and self.onchain.connected:
            tasks["curve"] = asyncio.create_task(self._get_bonding_data(address))
            tasks["price"] = asyncio.create_task(self._get_price_data(address))

        if self.acp.is_configured and token.agent_id:
            tasks["agent_details"] = asyncio.create_task(self.acp.get_agent_details(token.agent_id))
            tasks["agent_jobs"] = asyncio.create_task(self.acp.get_agent_jobs(token.agent_id, limit=50))
            tasks["agent_metrics"] = asyncio.create_task(self.acp.get_agent_metrics(token.agent_id))

        if not token.agent_id and self.acp.is_configured:
            name = token_info.get("name", "")
            if name:
                tasks["agent_search"] = asyncio.create_task(self.acp.search_agents(query=name, limit=5))

        if tasks:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            task_keys = list(tasks.keys())
            for i, result in enumerate(results):
                key = task_keys[i]
                if isinstance(result, Exception):
                    logger.warning("Enrichment task %s failed for %s: %s", key, address, result)
                    continue

                if key == "curve" and isinstance(result, dict):
                    token.bonding = BondingCurveState.from_onchain(result)
                    token.token_type = TokenType.GRADUATED if result.get("is_graduated") else TokenType.ON_CURVE

                elif key == "price" and isinstance(result, dict):
                    token.price.current_price = result.get("price", 0)
                    token.price.liquidity_usd = result.get("liquidity_usd", 0)

                elif key == "agent_details" and isinstance(result, dict):
                    token.name = result.get("name", token.name)
                    token.symbol = result.get("symbol", token.symbol)
                    token.description = result.get("description", "")
                    token.creator = result.get("creator", token.creator)
                    token.links = result.get("links", {})
                    token.logo_url = result.get("logo_url", "")

                elif key == "agent_jobs" and isinstance(result, list):
                    total_jobs = len(result)
                    completed = len([j for j in result if j.get("status") == "completed"])
                    token.usage.acp_jobs_total = total_jobs
                    token.usage.acp_jobs_24h = completed

                elif key == "agent_metrics" and isinstance(result, dict):
                    token.usage.estimated_revenue_usd = result.get("total_revenue_usd", 0)
                    token.accumulated_virtual = result.get("total_virtuals_earned", 0)

                elif key == "agent_search" and isinstance(result, list) and result:
                    agent = result[0]
                    token.agent_id = agent.get("id", agent.get("agent_id", ""))

        # Calculate alpha score
        alpha = self.surge_engine.calculate_alpha_score(token)
        token.alpha_score.overall_score = alpha["overall_score"]
        token.alpha_score.surge_component = alpha["surge_component"]
        token.alpha_score.usage_component = alpha["usage_component"]
        token.alpha_score.bonding_component = alpha["bonding_component"]
        token.alpha_score.trend_component = alpha["trend_component"]

        # Calculate surge score
        token.surge.overall_surge_score = self.surge_engine.calculate_surge_score(token)
        token.surge.is_surging = token.surge.overall_surge_score > 1.0

        return token

    async def _get_bonding_data(self, address: str) -> Dict[str, Any]:
        state = self.onchain.get_curve_state(address)
        if state:
            return state
        return {}

    async def _get_price_data(self, address: str) -> Dict[str, Any]:
        try:
            price = self.onchain.get_price(address)
            if price is not None:
                return {"price": price}
        except Exception:
            pass
        return {}

    # -- Single Token Detail --

    async def get_token_detail(self, address: str) -> Optional[TokenData]:
        cached = await self.cache.get(CacheClient.token_detail_key(address))
        if cached is not None:
            logger.debug("Token detail served from cache: %s", address)
            return TokenData(**cached)

        tokens = await self.get_enriched_token_list()
        for t in tokens:
            if t.address == address:
                await self.cache.set(CacheClient.token_detail_key(address), t.model_dump(), TTL_TOKEN_DETAIL)
                return t

        logger.warning("Token %s not found in aggregated list", address)
        return None

    # -- New Tokens --

    async def get_new_tokens(self, hours: int = 24) -> List[TokenData]:
        all_tokens = await self.get_enriched_token_list()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        new = []
        for t in all_tokens:
            if t.launched_at and t.launched_at >= cutoff:
                new.append(t)
        return sorted(new, key=lambda x: x.launched_at or datetime.min.replace(tzinfo=timezone.utc))

    # -- Surges --

    async def get_active_surges(self) -> List[Dict[str, Any]]:
        cached = await self.cache.get(CacheClient.surge_alerts_key())
        if cached is not None:
            return cached

        tokens = await self.get_enriched_token_list()
        alerts = self.surge_engine.detect_surges(tokens)
        if alerts:
            data = [a.model_dump() for a in alerts]
            await self.cache.set(CacheClient.surge_alerts_key(), data, 5)
            return data

        return []

    # -- Health --

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "acp_configured": self.acp.is_configured,
            "dune_configured": self.dune.is_configured,
            "onchain_connected": self.onchain.connected,
            "tokens_cached": len(self._tokens),
        }

    async def close(self) -> None:
        await self.cache.close()
        await self.acp.close()
