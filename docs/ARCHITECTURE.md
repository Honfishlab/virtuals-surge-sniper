# Architecture

## System Overview

### Flow: Discovery -> Enrichment -> Scoring -> Serving

1. **Discovery**: ACP list + on-chain TokenCreated events discover new tokens
2. **Enrichment**: Each token enriched with metrics from all sources in parallel
3. **Scoring**: Surge engine calculates surge multipliers and alpha scores
4. **Caching**: Results cached in Redis with configurable TTLs
5. **Serving**: FastAPI serves REST endpoints; WebSocket streams real-time surges
6. **Execution**: Surge Sniper (TypeScript) handles buy/sell via bondv5-trader

### Component Details

**Backend (FastAPI)**
- Aggregator: Combines ACP, Dune, on-chain with async parallel fetching
- Surge Engine: Detects volume/activity spikes using rolling window baselines
- Alpha Scorer: Weighted composite scoring (surge, usage, bonding, trend)
- Cache Layer: Redis with automatic serialization and configurable TTLs
- API Layer: REST + WebSocket for real-time updates

**Frontend (Next.js 15)**
- Token Universe Table: Sortable, filterable with real-time updates
- Token Detail: Bonding curve visualization, activity charts, alpha breakdown
- Surge Alerts: Live WebSocket feed with clickable navigation
- Snipe Modal: One-click execution with simulation results

**Key Design Decisions**
- Async throughout (httpx, web3, redis, asyncio)
- Parallel enrichment across data sources per token
- Cache-first: Redis checked before re-fetching
- Graceful degradation: Missing API keys fall back to on-chain only
- Simulation first: Snipe runs in simulation mode by default
