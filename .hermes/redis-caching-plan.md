# Redis Caching Plan — virtuals-surge-sniper

## Problem
Currently `get_enriched_token_list()` fetches data from on-chain RPC, ACP, and VP API on every request. When external calls hang, the API blocks for 30+ seconds. Seed-data fallback protects against total failure but doesn't solve the slow-path problem when discovery partially succeeds.

## Goals
1. **Never let a single slow source block the dashboard**
2. **Cache successful results so repeated requests are instant**
3. **Keep cache invalidation simple** (TTL-based, no complex purge logic)

## Cache Architecture

### What to cache
| Key Pattern | Content | TTL |
|---|---|---|
| `tokens:list` | Full enriched token list (from `get_enriched_token_list()`) | 60s |
| `token:detail:<addr>` | Single token detail object | 60s |
| `surges:active` | Active surge alerts | 10s |
| `discovery:chain` | Raw chain-discovered token addresses | 5m |
| `discovery:acp` | Raw ACP-discovered agent list | 5m |
| `discovery:vp` | Raw VP API token listings | 5m |

### Cache warm strategy
1. **On startup** — kick off background discovery tasks; cache their results when complete
2. **On API request** — serve from cache if present AND TTL not expired; otherwise run discovery with timeouts
3. **Async refresh** — once per minute, re-run discovery in background and update cache (no request blocking)

### Invalidation
- TTL-based only (no manual purge needed for v1)
- Seed data requests bypass cache entirely
- Health check endpoint doesn't touch cache

## Implementation Steps

### Phase 1 — Token list cache (priority: high)
**File:** `backend/app/cache/redis.py` — add `cache_token_list()` helper
**File:** `backend/app/data_aggregator/aggregator.py` — wrap `get_enriched_token_list()` with cache read/write

```python
# Pseudocode
async def get_enriched_token_list(self) -> List[TokenData]:
    cached = await self.cache.get(CacheClient.token_list_key())
    if cached is not None:
        logger.debug("Token list served from cache")
        return [TokenData(**t) if isinstance(t, dict) else t for t in cached]
    
    tokens = await self._discover_and_enrich_tokens()  # existing logic
    
    if tokens:
        data = [t.model_dump() for t in tokens]
        await self.cache.set(CacheClient.token_list_key(), data, 60)
    
    return tokens
```

### Phase 2 — Discovery cache (priority: medium)
Cache the raw results from each discovery source so that repeated requests don't hammer slow sources.

```python
async def _discover_tokens(self) -> List[Dict[str, Any]]:
    chain_key = "discovery:chain"
    acp_key = "discovery:acp"
    vp_key = "discovery:vp"
    
    # Try cache first
    chain_data = await self.cache.get(chain_key) or []
    acp_data = await self.cache.get(acp_key) or []
    vp_data = await self.cache.get(vp_key) or []
    
    # Kick off async refresh if stale or empty
    async def refresh(key, fetch_fn):
        nonlocal chain_data, acp_data, vp_data
        try:
            result = await asyncio.wait_for(fetch_fn(), timeout=3.0)
            data = result if isinstance(result, list) else []
            if data:
                await self.cache.set(key, data, 300)
                return data
        except Exception:
            pass
        return []
    
    if not chain_data:
        chain_data = await refresh(chain_key, self._discover_from_chain)
    if not acp_data:
        acp_data = await refresh(acp_key, self._discover_from_acp)
    if not vp_data:
        vp_data = await refresh(vp_key, self._discover_from_vp)
    
    # Merge (deduplicate by address)
    ...
```

### Phase 3 — Background cache warmup (priority: low)
Add a periodic task that re-caches token data every 60 seconds:

```python
# In main.py startup event
async def warm_cache_periodically():
    while True:
        await asyncio.sleep(60)
        try:
            tokens = await aggregator.get_enriched_token_list()
            if tokens:
                data = [t.model_dump() for t in tokens]
                await aggregator.cache.set(
                    CacheClient.token_list_key(), data, 60
                )
                logger.info("Background cache warm: %d tokens", len(tokens))
        except Exception:
            pass
```

### Phase 4 — Cache metrics (nice-to-have)
Add counters for cache hit/miss rates exposed via `/api/health` or metrics endpoint:

```python
# In CacheClient
self.hits = 0
self.misses = 0

def get(self, key):
    ...
    if value is not None:
        self.hits += 1
    else:
        self.misses += 1
```

## File Changes Summary

| File | Change |
|---|---|
| `backend/app/cache/redis.py` | Add `cache_token_list()` / `cache_token_detail()` helpers, hit/miss counters |
| `backend/app/data_aggregator/aggregator.py` | Wrap `get_enriched_token_list()` with cache read/write, cache discovery results |
| `backend/app/api/routes.py` | Add `cache-stats` endpoint |
| `backend/app/main.py` | Add periodic cache warmup task |

## Rollout Order
1. Phase 1 (token list cache) → test
2. Phase 2 (discovery cache) → test
3. Phase 3 (background warmup) → test
4. Phase 4 (metrics) → polish

## Success Criteria
- `/api/tokens` returns in < 200ms on cached hits
- No blocking on slow external calls
- Cache hit rate > 80% under normal usage