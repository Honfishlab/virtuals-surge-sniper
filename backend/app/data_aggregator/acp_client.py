"""
ACP (Agent Communication Protocol) API Client.

Base URL: https://api.acp.virtuals.io
Authentication: Bearer token via ACP_AUTH_TOKEN env var.

DO NOT use the old https://acp.virtuals.io or https://claw-api.virtuals.io domains.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ACP_BASE_URL = "https://api.acp.virtuals.io"


class ACPClient:
    """Async HTTP client for the ACP API (api.acp.virtuals.io)."""

    def __init__(self, token: str = "", base_url: str = ACP_BASE_URL) -> None:
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )
        self._initialized = bool(token)

    @property
    def is_configured(self) -> bool:
        return self._initialized

    # ── Agents ──────────────────────────────────────────────────────────

    async def search_agents(
        self,
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search for agents by name, description, or metadata.

        Returns list of agent dicts. Returns empty list on error.
        """
        try:
            resp = await self.client.get(
                "/agents/search",
                params={"q": query, "limit": limit, "offset": offset},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("agents", []) if isinstance(data, dict) else []
        except httpx.HTTPStatusError as exc:
            logger.error("ACP search_agents HTTP error %s: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.error("ACP search_agents error: %s", exc)
            return []

    async def get_agent_details(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full details for a single agent by ID."""
        try:
            resp = await self.client.get(f"/agents/{agent_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            # Accept both direct object and wrapped response
            if isinstance(data, dict) and "agent" in data:
                return data["agent"]
            return data if isinstance(data, dict) else None
        except httpx.HTTPStatusError as exc:
            logger.error("ACP get_agent_details HTTP error %s for %s", exc.response.status_code, agent_id)
            return None
        except Exception as exc:
            logger.error("ACP get_agent_details error: %s", exc)
            return None

    async def get_agent_jobs(
        self,
        agent_id: str,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get recent ACP job/activity for an agent (usage metric source)."""
        try:
            resp = await self.client.get(
                f"/agents/{agent_id}/jobs",
                params={"limit": limit, "offset": offset},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("jobs", []) if isinstance(data, dict) else []
        except httpx.HTTPStatusError as exc:
            logger.error("ACP get_agent_jobs HTTP error %s for %s", exc.response.status_code, agent_id)
            return []
        except Exception as exc:
            logger.error("ACP get_agent_jobs error: %s", exc)
            return []

    async def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get aggregate metrics for an agent (revenue, total jobs, etc.)."""
        try:
            resp = await self.client.get(f"/agents/{agent_id}/metrics")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "metrics" in data:
                return data["metrics"]
            return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.error("ACP get_agent_metrics error: %s", exc)
            return None

    async def list_agents(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "trending",
    ) -> List[Dict[str, Any]]:
        """List agents (sorted by popularity, trending, or new)."""
        try:
            resp = await self.client.get(
                "/agents",
                params={"limit": limit, "offset": offset, "sort_by": sort_by},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("agents", []) if isinstance(data, dict) else []
        except Exception as exc:
            logger.error("ACP list_agents error: %s", exc)
            return []

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()

    async def __aenter__(self) -> "ACPClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
