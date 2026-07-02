# Backend Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app
COPY backend/pyproject.toml .
COPY backend/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Final image ──────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY --from=builder /usr/local/lib/python3.11/site-packages \
    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn \
    /usr/local/bin/uvicorn

COPY backend/app app/app
COPY backend/pyproject.toml .
COPY scripts/seed_demo_data.py scripts/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
