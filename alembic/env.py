from __future__ import annotations

from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.infrastructure.postgres_dsn import normalize_sqlalchemy_postgres_dsn

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Project currently uses raw SQL migrations only.
target_metadata = None


def _get_database_url() -> str:
    raw = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    return normalize_sqlalchemy_postgres_dsn(raw)


def run_migrations_offline() -> None:
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
