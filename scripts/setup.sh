#!/bin/bash
# Setup script for Virtuals Surge Sniper
# Installs dependencies and prepares the environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Virtuals Surge Sniper Setup ==="
echo "Project: $PROJECT_DIR"

# ── Backend ─────────────────────────────────────────────────────────
echo ""
echo "Setting up Python backend..."

if command -v python3 &> /dev/null; then
    echo "  Python found: $(python3 --version)"
else
    echo "  ERROR: Python 3.11+ required"
    exit 1
fi

# Create virtual environment
if [ ! -d "$PROJECT_DIR/backend/.venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/backend/.venv"
fi

echo "  Activating venv and installing dependencies..."
source "$PROJECT_DIR/backend/.venv/bin/activate"
pip install --upgrade pip > /dev/null 2>&1
pip install -r "$PROJECT_DIR/backend/requirements.txt" > /dev/null 2>&1
echo "  Backend dependencies installed."

# ── Frontend ─────────────────────────────────────────────────────────
echo ""
echo "Setting up Next.js frontend..."

if command -v node &> /dev/null; then
    echo "  Node.js found: $(node --version)"
else
    echo "  WARNING: Node.js not found. Frontend requires Node.js 22+."
    echo "  Install: https://nodejs.org/en/download"
fi

if command -v npm &> /dev/null; then
    echo "  npm found: $(npm --version)"
    echo "  Installing frontend dependencies..."
    cd "$PROJECT_DIR/frontend"
    npm ci > /dev/null 2>&1 || npm install > /dev/null 2>&1
    echo "  Frontend dependencies installed."
else
    echo "  WARNING: npm not found."
fi

# ── Docker ────────────────────────────────────────────────────────────
echo ""
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    echo "  Docker found: $(docker --version)"
    echo "  To start with Docker: cd $PROJECT_DIR && docker-compose up"
else
    echo "  WARNING: Docker not found. Use setup services locally or install Docker."
fi

# ── Copy .env.example ────────────────────────────────────────────────
echo ""
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "  Created .env from .env.example — edit it with your keys."
else
    echo "  .env already exists, skipping."
fi

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys (ACP_AUTH_TOKEN, DUNE_API_KEY)"
echo "  2. Start backend:  cd $PROJECT_DIR/backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "  3. Start frontend: cd $PROJECT_DIR/frontend && npm run dev"
echo "  4. Or use Docker:  cd $PROJECT_DIR && docker-compose up"
echo "  5. Seed demo data: cd $PROJECT_DIR/backend && source .venv/bin/activate && python ../scripts/seed_demo_data.py"
echo ""
