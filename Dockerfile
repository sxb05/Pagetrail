# ── Stage 1: build the React frontend ────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python backend ───────────────────────────────────────────────
FROM python:3.11-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend

# Memory note: guardrails ML models (jailbreak + PII) consume ~350 MB RAM
# on first request.  On hosting plans with ≤ 512 MB RAM (e.g. Render free
# tier) set PAGETRAIL_GUARDRAILS=false in the service's environment
# variables to skip the transformer models while keeping regex checks active.
# Default here is "true" so that production / higher-memory deploys get
# full ML-based safety by default.
ENV PAGETRAIL_GUARDRAILS=true

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir -r backend/requirements.txt

# Pre-download the jailbreak model weights during the image build so the
# first request does not stall.  This step is a no-op when
# PAGETRAIL_GUARDRAILS=false because the model is never called.
RUN python -m guardrails_ai.detect_jailbreak.post_install

COPY backend ./backend

COPY --from=frontend-build /frontend/dist ./frontend/dist

RUN mkdir -p /app/uploads

EXPOSE 10000

# Use a single Uvicorn worker to stay inside the RAM budget on free-tier
# hosting (512 MB).  Increase workers on paid plans.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --log-level info"]
