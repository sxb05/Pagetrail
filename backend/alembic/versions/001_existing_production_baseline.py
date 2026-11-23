"""Existing production-era baseline.

Revision ID: 001_existing_production
Revises: none
"""

from alembic import context, op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "001_existing_production"
down_revision = None
branch_labels = None
depends_on = None


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


def _verify_existing_baseline(bind) -> None:
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names(schema="public"))
    existing_baseline = BASELINE_TABLES & existing_tables
    if not existing_baseline:
        return
    missing_tables = sorted(BASELINE_TABLES - existing_tables)
    if missing_tables:
        raise RuntimeError(
            "Existing database schema is partial and missing baseline tables: "
            + ", ".join(missing_tables)
        )

    mismatches = []
    for table_name, required_columns in BASELINE_COLUMNS.items():
        actual_columns = {
            column["name"]: column
            for column in inspector.get_columns(table_name, schema="public")
        }
        missing = sorted(set(required_columns) - set(actual_columns))
        if missing:
            mismatches.append(f"{table_name} missing columns: {', '.join(missing)}")
            continue

        pk = inspector.get_pk_constraint(table_name, schema="public")
        if set(pk.get("constrained_columns", [])) != BASELINE_PRIMARY_KEYS[table_name]:
            mismatches.append(f"{table_name} primary key")

    if mismatches:
        raise RuntimeError(
            "Existing database baseline verification failed: "
            + "; ".join(mismatches)
        )

    actual_vector_type = bind.execute(
        sa.text(
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
    if actual_vector_type != "vector(3072)":
        raise RuntimeError(
            "Existing database baseline verification failed: "
            "rag_documents.embedding_vector must be vector(3072), found "
            + (actual_vector_type or "missing")
        )


def upgrade() -> None:
    if context.is_offline_mode():
        # Static SQL generation cannot inspect a live schema.
        pass
    else:
        _verify_existing_baseline(op.get_bind())
        inspector = sa.inspect(op.get_bind())
        existing_tables = set(inspector.get_table_names(schema="public"))
        if BASELINE_TABLES.issubset(existing_tables):
            # Existing Pagetrail data is already present. This revision is a
            # forward-only baseline marker and makes no schema or data changes.
            return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index("ix_conversations_id", "conversations", ["id"], unique=False)
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["conversations.thread_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"], unique=False)
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"], unique=False)

    op.create_table(
        "long_term_memory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["conversations.thread_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_long_term_memory_id", "long_term_memory", ["id"], unique=False)
    op.create_index("ix_long_term_memory_user_id", "long_term_memory", ["user_id"], unique=False)

    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.Column("embedding_vector", Vector(3072), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_documents_thread_id", "rag_documents", ["thread_id"], unique=False)

    op.create_table(
        "checkpoints",
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("checkpoint_ns", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("checkpoint_id", sa.Text(), nullable=False),
        sa.Column("parent_checkpoint_id", sa.Text(), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("checkpoint", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "checkpoint_id"),
    )
    op.create_index("checkpoints_thread_id_idx", "checkpoints", ["thread_id"], unique=False)
    op.create_table(
        "checkpoint_blobs",
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("checkpoint_ns", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("blob", sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "channel", "version"),
    )
    op.create_index("checkpoint_blobs_thread_id_idx", "checkpoint_blobs", ["thread_id"], unique=False)
    op.create_table(
        "checkpoint_writes",
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("checkpoint_ns", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("checkpoint_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("blob", sa.LargeBinary(), nullable=False),
        sa.Column("task_path", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx"),
    )
    op.create_index("checkpoint_writes_thread_id_idx", "checkpoint_writes", ["thread_id"], unique=False)
    op.create_table(
        "checkpoint_migrations",
        sa.Column("v", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("v"),
    )
    op.create_table(
        "keep_alive_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("pinged_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    for table in ("users", "conversations", "chat_messages", "long_term_memory", "rag_documents"):
        op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))


def downgrade() -> None:
    raise RuntimeError("The baseline downgrade is destructive and is intentionally disabled.")
