"""
Virtuals Protocol API Client (vp-trade-sdk compatible).

Wraps the Virtuals REST API for reading token listings, klines, and trades.
Reads config from env vars: VIRTUAL_API_URL, VIRTUAL_API_URL_V2.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.virtuals.io"
DEFAULT_BASE_URL_V2 = "https://vp-api.virtuals.io"


def _to_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, handling string/None/other types safely."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class VirtualsAPIClient:
    """Async HTTP client for Virtuals Protocol REST API."""

    def __init__(
        self,
        api_url: str = DEFAULT_BASE_URL,
        api_url_v2: str = DEFAULT_BASE_URL_V2,
    ) -> None:
        self.base_url = api_url
        self.base_url_v2 = api_url_v2
        self.client: Optional[Any] = None  # Will be created lazily

    async def _get_client(self) -> Any:
        """Lazy initialization of async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"accept": "application/json"},
                timeout=10.0,
                follow_redirects=True,
            )
        return self.client

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None

    async def __aenter__(self) -> "VirtualsAPIClient":
        await self._get_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Token Listings ────────────────────────────────────────────

    async def get_token_listings(
        self,
        token_type: str = "SENTIENT",  # SENTIENT or PROTOTYPE
        page: int = 1,
        page_size: int = 50,
        chain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch a list of virtual agent tokens.

        token_type: SENTIENT (agent with bonding curve) or PROTOTYPE (early stage)
        chain: BASE, SOLANA, or None for all chains
        """
        params: Dict[str, str] = {
            "filters[status]": {
                "SENTIENT": "2",
                "PROTOTYPE": "1",
            }.get(token_type, ""),
            "sort[0]": "totalValueLocked:desc",
            "sort[1]": "createdAt:desc",
            "populate[0]": "image",
            "pagination[page]": str(page),
            "pagination[pageSize]": str(page_size),
        }

        if chain and chain.upper() in ("BASE", "SOLANA"):
            params["filters[chain]"] = chain.upper()

        try:
            client = await self._get_client()
            resp = await client.get("/api/virtuals", params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_tokens = data.get("data", [])
            return [self._normalize_token(t) for t in raw_tokens]
        except Exception as exc:
            logger.error("get_token_listings error: %s", exc)
            return []

    async def search_tokens(self, keyword: str) -> List[Dict[str, Any]]:
        """Search tokens by name, symbol, or address."""
        params: Dict[str, str] = {
            "filters[status]": "3",  # SEARCH
            "filters[$or][0][name][$contains]": keyword,
            "filters[$or][1][symbol][$contains]": keyword,
            "filters[$or][2][tokenAddress][$contains]": keyword,
            "filters[$or][3][preToken][$contains]": keyword,
            "sort[0]": "totalValueLocked:desc",
            "sort[1]": "createdAt:desc",
            "populate[0]": "image",
            "pagination[page]": "1",
            "pagination[pageSize]": "10",
        }

        try:
            client = await self._get_client()
            resp = await client.get("/api/virtuals", params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_tokens = data.get("data", [])
            return [self._normalize_token(t) for t in raw_tokens]
        except Exception as exc:
            logger.error("search_tokens error: %s", exc)
            return []

    # ── K-line Data ───────────────────────────────────────────────

    async def get_klines(
        self,
        token_address: str,
        granularity: int = 86400,  # 1 day in seconds
        start: int = 0,
        end: int = 0,
        limit: int = 30,
        chain_id: int = 0,  # 0 = BASE, 1 = SOLANA
    ) -> List[Dict[str, Any]]:
        """Fetch K-line (candlestick) data for a token.

        granularity: seconds (3600=1h, 86400=1d, 604800=1w)
        start/end: unix ms timestamps (0 = unlimited)
        chain_id: 0 = BASE, 1 = SOLANA
        """
        params: Dict[str, str] = {
            "tokenAddress": token_address,
            "granularity": str(granularity),
            "start": str(start),
            "end": str(end),
            "limit": str(limit),
            "chainID": str(chain_id),
        }

        try:
            resp = await httpx.AsyncClient(
                base_url=self.base_url_v2,
                headers={"accept": "application/json"},
                timeout=30.0,
            ).get("/vp-api/klines", params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_klines = data.get("data", {}).get("Klines", [])
            return [
                {
                    "open": float(k["open"]),
                    "high": float(k["high"]),
                    "low": float(k["low"]),
                    "close": float(k["close"]),
                    "volume": float(k["volume"]),
                    "start_ms": k["startInMilli"],
                    "end_ms": k["endInMilli"],
                    "start_utc": datetime.fromtimestamp(
                        k["startInMilli"] / 1000, tz=timezone.utc
                    ).isoformat(),
                    "granularity": k["granularity"],
                }
                for k in raw_klines
            ]
        except Exception as exc:
            logger.error("get_klines error: %s", exc)
            return []

    # ── Trades ────────────────────────────────────────────────────

    async def get_latest_trades(
        self,
        token_address: str,
        limit: int = 50,
        chain_id: int = 0,
        tx_sender: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch latest trades for a token."""
        params: Dict[str, str] = {
            "tokenAddress": token_address,
            "limit": str(limit),
            "chainID": str(chain_id),
        }
        if tx_sender:
            params["txSender"] = tx_sender

        try:
            resp = await httpx.AsyncClient(
                base_url=self.base_url_v2,
                headers={"accept": "application/json"},
                timeout=30.0,
            ).get("/vp-api/trades", params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_trades = data.get("data", {}).get("Trades", [])
            return [
                {
                    "tx_sender": t["txSender"],
                    "tx_hash": t["txHash"],
                    "token_address": t["tokenAddress"],
                    "is_buy": bool(t["isBuy"]),
                    "agent_token_amt": float(t["agentTokenAmt"]),
                    "virtual_token_amt": float(t["virtualTokenAmt"]),
                    "price": float(t["price"]),
                    "timestamp": t["timestamp"],
                    "timestamp_utc": datetime.fromtimestamp(
                        t["timestamp"], tz=timezone.utc
                    ).isoformat(),
                }
                for t in raw_trades
            ]
        except Exception as exc:
            logger.error("get_latest_trades error: %s", exc)
            return []

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _normalize_token(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a raw token from Virtuals API to our internal format.
        
        Handles None values gracefully for socials, image, etc.
        """
        socials = raw.get("socials") or {}
        verified = socials.get("VERIFIED_LINKS") or {}
        image = raw.get("image") or {}
        
        return {
            "id": raw.get("id", 0),
            "name": raw.get("name", ""),
            "symbol": raw.get("symbol", ""),
            "token_address": raw.get("tokenAddress") or raw.get("preToken", ""),
            "pre_token": raw.get("preToken", ""),
            "status": raw.get("status", ""),
            "lp_address": raw.get("lpAddress") or raw.get("preTokenPair", ""),
            "description": raw.get("description", ""),
            "holder_count": raw.get("holderCount", 0),
            "market_cap": raw.get("mcapInVirtual", 0),
            "total_value_locked": _to_float(raw.get("totalValueLocked"), 0.0),
            "chain": raw.get("chain", ""),
            "twitter": verified.get("TWITTER", ""),
            "telegram": verified.get("TELEGRAM", ""),
            "image_url": image.get("url", ""),
            "created_at": raw.get("createdAt", ""),
        }
