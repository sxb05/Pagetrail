from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import urlsplit

from alembic import context
from sqlalchemy import MetaData, engine_from_config, pool
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from app.db.base import Base
from app.db import models as _models  # noqa: F401
from app.services.rag import rag_documents

target_metadata = MetaData()
for table in Base.metadata.tables.values():
    table.to_metadata(target_metadata)
rag_documents.to_metadata(target_metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(str(ALEMBIC_INI))


def _migration_url() -> str:
    url = os.getenv("ALEMBIC_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "ALEMBIC_DATABASE_URL is required. Refuse to guess a migration target."
        )
    if url.startswith(("f\"", "f'", "F\"", "F'")):
        raise RuntimeError("ALEMBIC_DATABASE_URL must be a literal PostgreSQL URL.")
    parsed = make_url(url)
    if parsed.get_backend_name() not in {"postgresql", "postgres"}:
        raise RuntimeError("ALEMBIC_DATABASE_URL must use PostgreSQL.")
    if parsed.host is None:
        raise RuntimeError("ALEMBIC_DATABASE_URL must include a database host.")
    return url


def _target_description(url: str) -> str:
    parsed = make_url(url)
    return f"{parsed.host}:{parsed.port or 5432}/{parsed.database}"


migration_url = _migration_url()
config.set_main_option("sqlalchemy.url", migration_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    host_info = _target_description(migration_url)
    print(f"Applying migrations to: {host_info}")
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"sslmode": "require", "connect_timeout": 5},
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
