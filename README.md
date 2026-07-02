# Virtuals Surge Sniper

Professional-grade Virtuals Protocol intelligence dashboard + automated surge sniper execution engine. Built on Base mainnet.

## 🚀 Quick Start

```bash
# 1. Copy environment config
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys (Dune, ACP, etc.)

# 2. Start all services
docker-compose up -d

# 3. Open dashboard
# Frontend: http://localhost:3000
# API:     http://localhost:8080/api
# Health:  http://localhost:8080/api/health
```

## 🏗️ Architecture

```
virtuals-surge-sniper/
├── backend/app/              # FastAPI backend (port 8080)
│   ├── api/                  # HTTP routes + WebSocket handlers
│   │   ├── routes.py         # Token list, surge alerts, health endpoints
│   │   └── ws.py             # WebSocket server for real-time push
│   ├── cache/                # Redis caching layer
│   │   └── redis.py          # Cache client with TTL management
│   ├── data_aggregator/      # Multi-source data collection
│   │   ├── aggregator.py     # Main orchestrator — merges on-chain, ACP, VP API, Dune
│   │   ├── onchain_client.py # Web3 RPC client — bonding curve, price, events
│   │   ├── vp_api_client.py  # Virtuals Protocol API — token listings, agent data
│   │   ├── acp_client.py     # ACP CLI integration — agent metrics, jobs
│   │   ├── dune_client.py    # Dune Analytics — macro rankings, on-chain analytics
│   │   ├── bonding_curve.py  # Bonding curve state parser & math
│   │   └── seed_data.py      # Fallback demo tokens when external sources are down
│   ├── ingestion/            # Chain event parsing
│   │   └── chain_events.py   # Parses TokenCreated, Graduated, etc. from RPC logs
│   ├── processing/           # Signal generation
│   │   └── surge_engine.py   # Multi-factor surge detection engine
│   ├── models/               # Pydantic data models
│   ├── config.py             # Settings (Base RPC, contract addresses, thresholds)
│   └── main.py               # FastAPI app entry point
├── frontend/                 # Next.js dashboard (port 3000)
│   ├── app/                  # App Router pages
│   │   ├── page.tsx          # Main dashboard layout
│   │   └── layout.tsx        # Root layout with styles
│   ├── components/           # React components
│   │   ├── TokenUniverseTable.tsx  # Sortable token grid (name, age, bond%, alpha, surge)
│   │   └── SurgeAlertPanel.tsx     # Real-time surge notification panel
│   ├── lib/
│   │   └── api.ts            # HTTP client + WebSocket client wrapper
│   ├── Dockerfile
│   └── next.config.ts        # API proxy rewrites for /api and /ws
├── execution/
│   └── sniper.py             # Surge sniper execution engine (TBD)
├── scripts/
│   ├── setup.sh              # Initial environment setup
│   └── seed_demo_data.py     # Demo data generation script
├── shared/
│   └── types.py              # Shared TypeScript ↔ Python type definitions
├── docs/
│   └── ARCHITECTURE.md       # Detailed architecture documentation
├── docker-compose.yml        # Docker orchestration (backend, frontend, redis)
├── .env.example              # Environment variable template
└── README.md                 # This file
```

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/tokens?limit=N&sort_by=alpha_score&sort_order=desc` | Enriched token list |
| `GET` | `/api/tokens/{address}` | Single token detail |
| `GET` | `/api/surges` | Active surge alerts |
| `GET` | `/api/new-tokens?hours=24` | Recently discovered tokens |
| `WS` | `/ws/surges` | Real-time surge alerts |
| `WS` | `/ws/token/{address}` | Real-time token updates |

### Query Parameters for `/api/tokens`

| Param | Options | Default |
|-------|---------|---------|
| `limit` | 1–100 | 50 |
| `sort_by` | `alpha_score`, `surge_multiplier`, `age_days`, `bonding_progress` | `alpha_score` |
| `sort_order` | `asc`, `desc` | `desc` |

## 📊 Data Sources

| Source | Purpose | Status |
|--------|---------|--------|
| Base RPC (on-chain) | Bonding curve state, token events, price | Active (5s timeout + fallback) |
| Virtuals Protocol API | Token listings, agent data, market metrics | Active (5s timeout + fallback) |
| ACP CLI | Agent job counts, usage stats, revenue | Configurable via auth token |
| Dune Analytics | Macro rankings, on-chain analytics | Optional — requires API key |
| Seed data | Fallback demo tokens when sources are unavailable | Always available |

## 🔧 Configuration

Copy `backend/.env.example` to `backend/.env` and fill in your keys:

```bash
# Required
BASE_RPC_URL=https://mainnet.base.org
REDIS_URL=redis://localhost:6379/0

# Virtuals Protocol contracts
FACTORY_ADDRESS=0x1a540088125d00dd3990f9da45ca0859af4d3b01
BONDING_V5_ADDRESS=0x1a540088125d00dd3990f9da45ca0859af4d3b01
VIRTUAL_TOKEN_ADDRESS=0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b

# Optional
DUNE_API_KEY=your_dune_key_here
ACP_AUTH_TOKEN=your_acp_token_here
```

## 🎯 Surge Engine

The surge detection engine evaluates tokens across multiple factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Surge component** | 35% | Volume/activity multiplier spikes |
| **Usage component** | 30% | ACP job counts, inference calls |
| **Bonding component** | 20% | Bonding curve progress, VIRTUAL locked |
| **Trend component** | 15% | Price momentum, social signals |

A token is flagged as "surging" when its composite score exceeds the threshold (default: 1.0).

## 🐳 Docker Deployment

```yaml
services:
  backend:      # FastAPI + WebSocket    → port 8080
  frontend:     # Next.js dashboard      → port 3000
  redis:        # In-memory cache         → port 6379
```

## 📝 Development

```bash
# Backend venv (ARM64 — DGX Spark / Apple Silicon compatible)
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend dev server
cd frontend
npm install
npm run dev          # http://localhost:3000
```

## 📄 License

MIT