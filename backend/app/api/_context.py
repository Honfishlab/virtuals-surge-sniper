"""Shared aggregator singleton between routes and ws modules."""

from __future__ import annotations

from typing import Optional

from app.data_aggregator.aggregator import VirtualsDataAggregator

_aggregator: Optional[VirtualsDataAggregator] = None


def get_aggregator() -> VirtualsDataAggregator:
    """Lazy singleton aggregator."""
    global _aggregator
    if _aggregator is None:
        _aggregator = VirtualsDataAggregator()
    return _aggregator
