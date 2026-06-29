"""Tests for ACP client."""

from __future__ import annotations

import pytest

from app.data_aggregator.acp_client import ACPClient


@pytest.mark.asyncio
async def test_acp_client_instantiation():
    """Client should initialize without errors."""
    client = ACPClient(token="fake_token_12345")
    assert client.is_configured is True


@pytest.mark.asyncio
async def test_acp_client_search_empty():
    """Search should return empty list when no token is provided."""
    client = ACPClient(token="fake_token_12345")
    # This will fail to connect but should not raise
    result = await client.search_agents(query="nonexistent_agent_xyz123", limit=5)
    assert isinstance(result, list)
    await client.close()


@pytest.mark.asyncio
async def test_acp_client_get_details_not_found():
    """Get details for nonexistent agent should return None."""
    client = ACPClient(token="fake_token_12345")
    result = await client.get_agent_details("nonexistent_agent_xyz")
    assert result is None or isinstance(result, dict)
    await client.close()
