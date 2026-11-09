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
# Default to regex-only safety so the container can start on Render's
# 512 MB tier. Set PAGETRAIL_GUARDRAILS=true on higher-memory deployments
# to enable the transformer-based checks.
ENV PAGETRAIL_GUARDRAILS=false

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir -r backend/requirements.txt

# Download ML detector weights only when ML guardrails are explicitly enabled.
# Keep the low-memory Render build free of unused model artifacts and setup work.
RUN if [ "$PAGETRAIL_GUARDRAILS" = "true" ]; then \
      python -m guardrails_ai.detect_jailbreak.post_install; \
    else \
      echo "Skipping Guardrails model download (PAGETRAIL_GUARDRAILS=false)"; \
    fi

COPY backend ./backend

COPY --from=frontend-build /frontend/dist ./frontend/dist

RUN mkdir -p /app/uploads

EXPOSE 10000

# Use a single Uvicorn worker to stay inside the RAM budget on free-tier
# hosting (512 MB).  Increase workers on paid plans.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --log-level info"]
