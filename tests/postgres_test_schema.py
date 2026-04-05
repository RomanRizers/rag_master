from __future__ import annotations

import psycopg


SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS documents(
        document_id UUID PRIMARY KEY,
        file_name TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        size_bytes BIGINT NOT NULL,
        status TEXT NOT NULL,
        source_name TEXT,
        tags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
        knowledge_base TEXT NOT NULL DEFAULT 'default',
        created_at TIMESTAMPTZ NOT NULL,
        object_key TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_jobs(
        job_id UUID PRIMARY KEY,
        document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
        status TEXT NOT NULL,
        progress INTEGER NOT NULL,
        attempt INTEGER NOT NULL DEFAULT 0,
        error_code TEXT,
        error_message TEXT,
        started_at TIMESTAMPTZ,
        finished_at TIMESTAMPTZ
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_sessions(
        session_id UUID PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages(
        message_id UUID PRIMARY KEY,
        session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        citations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_document_id ON ingestion_jobs(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at)",
]


def ensure_test_schema(dsn: str):
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for statement in SCHEMA_SQL:
                cursor.execute(statement)
