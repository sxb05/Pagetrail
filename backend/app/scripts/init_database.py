import logging

from sqlalchemy import text

from app.db.session import admin_engine, init_db
from app.services.rag import init_rag_db

logger = logging.getLogger("pagetrail.database")


def main() -> None:
    """Initialize the existing application and RAG schema without touching data."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info("Checking PostgreSQL pgvector extension")
    with admin_engine.connect() as connection:
        vector_enabled = connection.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar()

    if not vector_enabled:
        raise RuntimeError(
            "The PostgreSQL pgvector extension is not enabled. Run "
            "'CREATE EXTENSION IF NOT EXISTS vector;' in the Supabase SQL Editor, "
            "then rerun this command."
        )

    logger.info("Creating/updating the RAG document table")
    init_rag_db()

    logger.info("Creating application tables and applying additive RLS/column setup")
    init_db()

    logger.info("PageTrail database initialization completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("PageTrail database initialization failed")
        raise
