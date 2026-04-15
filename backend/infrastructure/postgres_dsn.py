from __future__ import annotations


def normalize_psycopg_postgres_dsn(dsn: str) -> str:
    value = (dsn or "").strip()
    if not value:
        return value
    if value.startswith("postgresql+psycopg://"):
        return "postgresql://" + value[len("postgresql+psycopg://") :]
    return value


def normalize_sqlalchemy_postgres_dsn(dsn: str) -> str:
    value = normalize_psycopg_postgres_dsn(dsn)
    if not value:
        return value
    if value.startswith("postgresql+"):
        return value
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value
