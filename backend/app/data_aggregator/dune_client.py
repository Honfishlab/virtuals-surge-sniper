"""
Dune Analytics API Client.

Wraps the Dune REST API to fetch agent rankings, volume trends,
and macro-level Virtuals Protocol data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DUNE_BASE_URL = "https://api.dune.com/api/v1"


class DuneClient:
    """Async HTTP client for Dune Analytics REST API."""

    def __init__(self, api_key: str = "", base_url: str = DUNE_BASE_URL) -> None:
        self.base_url = base_url
        self.headers: Dict[str, str] = {
            "X-Dune-API-Key": api_key,
            "Content-Type": "application/json",
        } if api_key else {}
        self._has_key = bool(api_key)
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers=self.headers,
            timeout=60.0,
            follow_redirects=True,
        )

    @property
    def is_configured(self) -> bool:
        return self._has_key

    # ── Query Execution ─────────────────────────────────────────────────

    async def execute_query(
        self,
        query_id: int,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute (or fetch results for) a Dune query by ID.

        First call returns execution state; subsequent calls poll for results.
        """
        try:
            resp = await self.client.get(
                f"/query/{query_id}/results",
                params={"cursor": cursor} if cursor else None,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Dune execute_query HTTP error %s for query %s: %s",
                         exc.response.status_code, query_id, exc)
            return None
        except Exception as exc:
            logger.error("Dune execute_query error: %s", exc)
            return None

    async def get_latest_results(
        self,
        query_id: int,
        page_size: int = 1000,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Poll a query until its results are ready, then return all rows.

        Retries up to 30 times with 2s backoff for slow queries.
        Returns empty list on failure.
        """
        for attempt in range(30):
            data = await self.execute_query(query_id, cursor=cursor)
            if data is None:
                return []

            state = data.get("execution_status", {}).get("status", "")
            if state == "QUERY_STATUS_COMPLETED":
                rows = data.get("result", {}).get("rows", [])
                return rows[:page_size]

            if state in ("QUERY_STATUS_FAILED", "QUERY_STATUS_CANCELLED"):
                logger.warning("Dune query %s failed: %s", query_id, data.get("error"))
                return []

            # Still running — wait and retry
            await self._sleep(2)
        else:
            logger.warning("Dune query %s timed out after 30 attempts", query_id)
            return []

    async def set_query_tags(self, query_id: int, tags: List[str]) -> bool:
        """Tag a saved query with custom tags."""
        try:
            resp = await self.client.post(
                f"/query/{query_id}/tags",
                json={"tags": tags},
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Dune set_query_tags error: %s", exc)
            return False

    # ── Query Management ────────────────────────────────────────────────

    async def get_query_metadata(self, query_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata (description, SQL, tags, etc.) for a query."""
        try:
            resp = await self.client.get(f"/query/{query_id}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", data)
        except Exception as exc:
            logger.error("Dune get_query_metadata error: %s", exc)
            return None

    async def cancel_query(self, execution_id: str) -> bool:
        """Cancel a running query execution."""
        try:
            resp = await self.client.delete(f"/query/{execution_id}/cancel")
            return resp.status_code == 200
        except Exception as exc:
            logger.error("Dune cancel_query error: %s", exc)
            return False

    # ── Helpers ─────────────────────────────────────────────────────────

    async def _sleep(self, seconds: float) -> None:
        await self.client.__dict__.get("_sleep", lambda _: None)(seconds)
        import asyncio
        await asyncio.sleep(seconds)

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "DuneClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


# ── Built-in Virtuals queries ─────────────────────────────────────────
# Replace with your actual Dune query IDs.

VIRTUALS_AGENT_VOLUME_QUERY_ID = 5432101  # placeholder — create on dune.com
VIRTUALS_NEW_TOKENS_QUERY_ID = 5432102   # placeholder
VIRTUALS_HOLDER_DIST_QUERY_ID = 5432103   # placeholder
