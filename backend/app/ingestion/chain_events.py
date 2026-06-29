"""
On-chain event listener for Virtuals Protocol.

Listens for:
- TokenCreated events (new token launches)
- BondPurchase events (bonding activity)
- BondGraduated events (graduation to Uniswap)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from web3 import Web3
from web3.types import LogReceipt

from app.data_aggregator.onchain_client import (
    OnChainClient,
    BONDING_EVENTS,
    FACTORY_ABI,
)

logger = logging.getLogger(__name__)


class ChainEventWatcher:
    """Watches on-chain events for Virtuals Protocol."""

    def __init__(self, onchain: OnChainClient) -> None:
        self.onchain = onchain
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._check_interval = 10  # seconds between polls

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def start(self) -> None:
        """Start watching for on-chain events."""
        self._running = True
        logger.info("Chain event watcher started")
        await self._watch_loop()

    async def stop(self) -> None:
        """Stop the watcher."""
        self._running = False
        logger.info("Chain event watcher stopped")

    async def _watch_loop(self) -> None:
        """Main polling loop."""
        last_block = self.onchain.get_current_block() - 1000  # start 1000 blocks back
        while self._running:
            try:
                current_block = self.onchain.get_current_block()
                new_events = await self._scan_block_range(last_block + 1, current_block)
                for event in new_events:
                    await self._dispatch_event(event)
                last_block = current_block
            except Exception as exc:
                logger.error("Watch loop error: %s", exc)

            await asyncio.sleep(self._check_interval)

    async def _scan_block_range(self, from_block: int, to_block: int) -> List[Dict[str, Any]]:
        """Scan a range of blocks for new events."""
        if from_block > to_block:
            return []

        events: List[Dict[str, Any]] = []

        # Token created events
        created = self.onchain.get_token_created_events(
            from_block=from_block,
            to_block=to_block,
            limit=500,
        )
        for ev in created:
            ev["type"] = "TokenCreated"
            events.append(ev)

        # Bond purchase events (for all known tokens, limit to recent blocks)
        # In production, this would use a subscription or indexed events
        bonds = self.onchain.get_bonding_events(
            token_address="",  # empty = all tokens (limit by block)
            from_block=from_block,
            to_block=to_block,
            limit=500,
        )
        for ev in bonds:
            ev["type"] = "BondPurchase"
            events.append(ev)

        return events

    async def _dispatch_event(self, event: Dict[str, Any]) -> None:
        """Dispatch an event to registered handlers."""
        event_type = event.pop("type", "unknown")
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error("Event handler error for %s: %s", event_type, exc)

    # -- Convenience methods --

    def get_recent_events(self, block_range: int = 5000) -> List[Dict[str, Any]]:
        """Get events from the last N blocks."""
        current = self.onchain.get_current_block()
        return self._scan_block_range(current - block_range, current)
