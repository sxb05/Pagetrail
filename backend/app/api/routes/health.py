import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import DATABASE_CONFIGURED, engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/api/health")
@router.get("/health/live")
def liveness() -> dict[str, str]:
    """Confirm the web process is running; do not depend on external services."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> dict[str, str]:
    """Check that PostgreSQL can answer a bounded, read-only readiness query."""
    if not DATABASE_CONFIGURED:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured.",
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed: PostgreSQL is unavailable")
        raise HTTPException(
            status_code=503,
            detail="Database is temporarily unavailable.",
        ) from None

    return {"status": "ready", "database": "ok"}
