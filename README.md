# Virtuals Surge Sniper

A professional-grade Virtuals Protocol intelligence dashboard + automated surge sniper execution engine.

## Architecture

- **Brain & Eyes**: Superior full-information dashboard with real-time metrics
- **Surge Sniper**: High-frequency, minimal-gas execution engine

## Project Structure

```
virtuals-surge-sniper/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DASHBOARD_SPEC.md
│   └── ACP_INTEGRATION.md
├── backend/            # Python FastAPI (Data Layer + Brain)
│   ├── app/
│   │   ├── data_aggregator/
│   │   ├── ingestion/
│   │   ├── processing/
│   │   └── api/
├── execution/          # TypeScript (Surge Sniper)
├── frontend/           # Next.js (Superior Dashboard)
├── shared/             # Shared types & utilities
└── scripts/            # Utility scripts
```

## Tech Stack

- **Backend**: Python FastAPI + Redis
- **Data Layer**: Dedicated aggregator service (ACP, Dune, on-chain)
- **Execution**: TypeScript (bondv5-trader)
- **Frontend**: Next.js 15 (professional terminal UI)

## Quick Start

```bash
docker-compose up -d
```

## License

MIT
