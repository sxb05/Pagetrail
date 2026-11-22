import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))


BASELINE_TABLES = {
    "users",
    "conversations",
    "chat_messages",
    "long_term_memory",
    "rag_documents",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
    "checkpoint_migrations",
    "keep_alive_logs",
}

PROJECT_OPERATION_TABLES = {
    "organizations",
    "organization_members",
    "projects",
    "project_members",
    "milestones",
    "tasks",
    "task_dependencies",
    "project_documents",
    "meeting_notes",
    "agent_runs",
    "agent_approvals",
    "agent_events",
    "agent_artifacts",
    "agent_schedules",
    "integration_connections",
    "audit_logs",
}

BASELINE_COLUMNS = {
    "users": {"id", "username", "password_hash", "email", "google_sub"},
    "conversations": {"id", "thread_id", "user_id", "name", "created_at", "updated_at"},
    "chat_messages": {"id", "thread_id", "user_id", "role", "content", "created_at", "updated_at"},
    "long_term_memory": {"id", "thread_id", "user_id", "content", "created_at", "updated_at"},
    "rag_documents": {"id", "thread_id", "content", "source", "embedding", "embedding_vector"},
    "checkpoints": {"thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id", "type", "checkpoint", "metadata"},
    "checkpoint_blobs": {"thread_id", "checkpoint_ns", "channel", "version", "type", "blob"},
    "checkpoint_writes": {"thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path"},
    "checkpoint_migrations": {"v"},
    "keep_alive_logs": {"id", "pinged_at"},
}


def main() -> int:
    url_value = os.getenv("ALEMBIC_DATABASE_URL", "").strip()
    if not url_value:
        raise RuntimeError("ALEMBIC_DATABASE_URL is required")

    url = make_url(url_value)
    if url.get_backend_name() not in {"postgresql", "postgres"} or not url.host:
        raise RuntimeError("ALEMBIC_DATABASE_URL must be a PostgreSQL URL")

    engine = create_engine(url_value, pool_pre_ping=True, connect_args={"sslmode": "require", "connect_timeout": 5})
    with engine.connect() as connection:
        existing = set(inspect(connection).get_table_names(schema="public"))
        missing_baseline = sorted(BASELINE_TABLES - existing)
        if missing_baseline:
            raise RuntimeError(
                "Production baseline verification failed; missing tables: "
                + ", ".join(missing_baseline)
            )

        inspector = inspect(connection)
        missing_columns = []
        for table_name, required_columns in BASELINE_COLUMNS.items():
            actual_columns = {
                column["name"]
                for column in inspector.get_columns(table_name, schema="public")
            }
            missing = sorted(required_columns - actual_columns)
            if missing:
                missing_columns.append(f"{table_name}({', '.join(missing)})")
        if missing_columns:
            raise RuntimeError(
                "Production baseline verification failed; missing columns: "
                + "; ".join(missing_columns)
            )

        existing_project_tables = sorted(PROJECT_OPERATION_TABLES & existing)
        if existing_project_tables:
            raise RuntimeError(
                "Project-operation migration target is not clean; existing tables: "
                + ", ".join(existing_project_tables)
            )

        if inspect(connection).has_table("alembic_version", schema="public"):
            revisions = [
                row[0]
                for row in connection.execute(text("SELECT version_num FROM public.alembic_version")).all()
            ]
            if revisions and revisions != ["001_existing_production"]:
                raise RuntimeError(
                    "Unexpected Alembic revision state. Expected no revision or "
                    "001_existing_production."
                )

    print(
        f"Migration preflight passed for {url.host}:{url.port or 5432}/{url.database}; "
        "baseline tables present, no project-operation tables present."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Migration preflight refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
