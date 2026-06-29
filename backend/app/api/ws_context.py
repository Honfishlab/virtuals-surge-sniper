"""WS context — aggregator singleton shared between routes and ws endpoints."""

from __future__ import annotations

from typing import Optional

from app.data_aggregator.aggregator import VirtualsDataAggregator

_aggregator: Optional[VirtualsDataAggregator] = None


def get_aggregator() -> VirtualsDataAggregator:
    """Lazy singleton aggregator (shared by routes and ws)."""
    global _aggregator
    if _aggregator is None:
        _aggregator = VirtualsDataAggregator()
    return _aggregator
