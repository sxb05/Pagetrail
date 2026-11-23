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

BASELINE_COLUMN_SPECS = {
    "users": {
        "id": ("integer", False),
        "username": ("string", False),
        "password_hash": ("string", True),
        "email": ("string", True),
        "google_sub": ("string", True),
    },
    "conversations": {
        "id": ("integer", False),
        "thread_id": ("string", False),
        "user_id": ("integer", True),
        "name": ("string", False),
        "created_at": ("string", True),
        "updated_at": ("string", True),
    },
    "chat_messages": {
        "id": ("integer", False),
        "thread_id": ("string", False),
        "user_id": ("integer", True),
        "role": ("string", False),
        "content": ("text", False),
        "created_at": ("string", True),
        "updated_at": ("string", True),
    },
    "long_term_memory": {
        "id": ("integer", False),
        "thread_id": ("string", True),
        "user_id": ("integer", True),
        "content": ("text", False),
        "created_at": ("string", True),
        "updated_at": ("string", True),
    },
    "rag_documents": {
        "id": ("string", False),
        "thread_id": ("string", False),
        "content": ("text", False),
        "source": ("string", False),
        "embedding": ("text", False),
        "embedding_vector": ("vector", True),
    },
    "checkpoints": {
        "thread_id": ("text", False),
        "checkpoint_ns": ("text", False),
        "checkpoint_id": ("text", False),
        "parent_checkpoint_id": ("text", True),
        "type": ("text", True),
        "checkpoint": ("jsonb", False),
        "metadata": ("jsonb", False),
    },
    "checkpoint_blobs": {
        "thread_id": ("text", False),
        "checkpoint_ns": ("text", False),
        "channel": ("text", False),
        "version": ("text", False),
        "type": ("text", False),
        "blob": ("binary", True),
    },
    "checkpoint_writes": {
        "thread_id": ("text", False),
        "checkpoint_ns": ("text", False),
        "checkpoint_id": ("text", False),
        "task_id": ("text", False),
        "idx": ("integer", False),
        "channel": ("text", False),
        "type": ("text", True),
        "blob": ("binary", False),
        "task_path": ("text", False),
    },
    "checkpoint_migrations": {"v": ("integer", False)},
    "keep_alive_logs": {
        "id": ("bigint", False),
        "pinged_at": ("datetime", True),
    },
}

BASELINE_PRIMARY_KEYS = {
    "users": {"id"},
    "conversations": {"id"},
    "chat_messages": {"id"},
    "long_term_memory": {"id"},
    "rag_documents": {"id"},
    "checkpoints": {"thread_id", "checkpoint_ns", "checkpoint_id"},
    "checkpoint_blobs": {"thread_id", "checkpoint_ns", "channel", "version"},
    "checkpoint_writes": {"thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx"},
    "checkpoint_migrations": {"v"},
    "keep_alive_logs": {"id"},
}

BASELINE_FOREIGN_KEYS = {
    "conversations": {("user_id", "users", "id")},
    "chat_messages": {("thread_id", "conversations", "thread_id"), ("user_id", "users", "id")},
    "long_term_memory": {("thread_id", "conversations", "thread_id"), ("user_id", "users", "id")},
}

BASELINE_UNIQUE_CONSTRAINTS = {
    "users": {("username",), ("email",), ("google_sub",)},
    "conversations": {("thread_id",)},
}

BASELINE_REQUIRED_INDEXES = {
    "users": {"ix_users_id", "ix_users_username"},
    "conversations": {"ix_conversations_id", "ix_conversations_user_id"},
    "chat_messages": {"ix_chat_messages_id", "ix_chat_messages_user_id"},
    "long_term_memory": {"ix_long_term_memory_id", "ix_long_term_memory_user_id"},
    "rag_documents": {"ix_rag_documents_thread_id"},
    "checkpoints": {"checkpoints_thread_id_idx"},
    "checkpoint_blobs": {"checkpoint_blobs_thread_id_idx"},
    "checkpoint_writes": {"checkpoint_writes_thread_id_idx"},
}


def type_matches(column_type, expected: str) -> bool:
    name = str(column_type).lower()
    class_name = column_type.__class__.__name__.lower()
    if expected == "integer":
        return "int" in name or "integer" in class_name
    if expected == "bigint":
        return "bigint" in name or "bigint" in class_name
    if expected == "string":
        return "varchar" in name or "character varying" in name or "string" in class_name
    if expected == "text":
        return "text" in name
    if expected == "vector":
        return "vector" in name
    if expected == "jsonb":
        return "jsonb" in name
    if expected == "binary":
        return "bytea" in name or "largebinary" in class_name
    if expected == "datetime":
        return "timestamp" in name or "datetime" in class_name
    return False


def main() -> int:
    url_value = os.getenv("ALEMBIC_DATABASE_URL", "").strip()
    if not url_value:
        raise RuntimeError("ALEMBIC_DATABASE_URL is required")

    url = make_url(url_value)
    if url.get_backend_name() not in {"postgresql", "postgres"} or not url.host:
        raise RuntimeError("ALEMBIC_DATABASE_URL must be a PostgreSQL URL")
    expected_host = os.getenv("EXPECTED_DATABASE_HOST", "").strip().lower()

    if not expected_host:
        raise RuntimeError("EXPECTED_DATABASE_HOST is required")

    if url.host.strip().lower() != expected_host:
        raise RuntimeError(
            f"Database host mismatch: expected {expected_host}, "
            f"received {url.host}"
    )    

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
        type_mismatches = []
        for table_name, required in BASELINE_COLUMN_SPECS.items():
            if table_name == "rag_documents":
                rag_catalog_columns = {
                    row.column_name: {
                        "nullable": row.is_nullable == "YES",
                        "type": row.data_type,
                    }
                    for row in connection.execute(
                        text(
                            """
                            SELECT column_name, is_nullable, data_type
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'rag_documents'
                            """
                        )
                    )
                }
                missing = sorted(set(required) - set(rag_catalog_columns))
                if missing:
                    missing_columns.append(f"{table_name}({', '.join(missing)})")
                    continue
                for column_name, (expected_type, nullable) in required.items():
                    if expected_type == "vector":
                        continue
                    catalog_column = rag_catalog_columns[column_name]
                    if catalog_column["nullable"] != nullable:
                        type_mismatches.append(
                            f"{table_name}.{column_name} expected "
                            f"{'nullable' if nullable else 'not nullable'}"
                        )
                continue
            actual = {
                column["name"]: column
                for column in inspector.get_columns(table_name, schema="public")
            }
            missing = sorted(set(required) - set(actual))
            if missing:
                missing_columns.append(f"{table_name}({', '.join(missing)})")
                continue
            for column_name, (expected_type, nullable) in required.items():
                column = actual[column_name]
                if expected_type == "vector":
                    if bool(column["nullable"]) != nullable:
                        type_mismatches.append(
                            f"{table_name}.{column_name} expected "
                            f"{'nullable' if nullable else 'not nullable'}"
                        )
                    continue
                if not type_matches(column["type"], expected_type):
                    type_mismatches.append(
                        f"{table_name}.{column_name} expected {expected_type}"
                    )
                if bool(column["nullable"]) != nullable:
                    type_mismatches.append(
                        f"{table_name}.{column_name} expected "
                        f"{'nullable' if nullable else 'not nullable'}"
                    )
        vector_type = connection.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod) AS actual_type
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'rag_documents'
                  AND a.attname = 'embedding_vector'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """
            )
        ).scalar_one_or_none()
        if vector_type != "vector(3072)":
            type_mismatches.append(
                f"rag_documents.embedding_vector expected vector(3072), "
                f"found {vector_type or 'missing'}"
            )
        if missing_columns:
            raise RuntimeError(
                "Production baseline verification failed; missing columns: "
                + "; ".join(missing_columns)
            )
        if type_mismatches:
            raise RuntimeError(
                "Production baseline verification failed; mismatches: "
                + "; ".join(type_mismatches)
            )

        structural_mismatches = []
        for table_name, expected_pk in BASELINE_PRIMARY_KEYS.items():
            pk = inspector.get_pk_constraint(table_name, schema="public")
            if set(pk.get("constrained_columns", [])) != expected_pk:
                structural_mismatches.append(f"{table_name} primary key")
        for table_name, expected_fks in BASELINE_FOREIGN_KEYS.items():
            actual = {
                (
                    tuple(foreign_key["constrained_columns"]),
                    foreign_key["referred_table"],
                    tuple(foreign_key["referred_columns"]),
                )
                for foreign_key in inspector.get_foreign_keys(table_name, schema="public")
            }
            normalized_expected = {
                (
                    (source,),
                    referred_table,
                    (referred_column,),
                )
                for source, referred_table, referred_column in expected_fks
            }
            if not normalized_expected.issubset(actual):
                structural_mismatches.append(f"{table_name} foreign keys")
        for table_name, expected_uniques in BASELINE_UNIQUE_CONSTRAINTS.items():
            actual_uniques = {
                tuple(unique["column_names"])
                for unique in inspector.get_unique_constraints(table_name, schema="public")
            }
            actual_uniques.update(
                tuple(index["column_names"])
                for index in inspector.get_indexes(table_name, schema="public")
                if index["unique"]
            )
            if not expected_uniques.issubset(actual_uniques):
                structural_mismatches.append(f"{table_name} unique constraints")
        for table_name, expected_indexes in BASELINE_REQUIRED_INDEXES.items():
            actual_indexes = {
                index["name"]
                for index in inspector.get_indexes(table_name, schema="public")
            }
            if not expected_indexes.issubset(actual_indexes):
                structural_mismatches.append(f"{table_name} indexes")
        if structural_mismatches:
            raise RuntimeError(
                "Production baseline verification failed; mismatches: "
                + "; ".join(structural_mismatches)
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
