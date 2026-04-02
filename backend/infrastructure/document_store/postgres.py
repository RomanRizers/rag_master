from __future__ import annotations

import json
from threading import RLock

import psycopg

from backend.infrastructure.document_store.base import DocumentStore


class PostgresDocumentStore(DocumentStore):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._lock = RLock()
        self._conn = psycopg.connect(dsn)
        self._conn.autocommit = True
        self._ensure_schema()

    def create_document(self, document: dict) -> dict:
        query = """
            INSERT INTO documents(
                document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, created_at, object_key
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                query,
                (
                    document["document_id"],
                    document["file_name"],
                    document["mime_type"],
                    int(document["size_bytes"]),
                    document["status"],
                    document.get("source_name"),
                    json.dumps(document.get("tags") or [], ensure_ascii=False),
                    document["created_at"],
                    document["object_key"],
                ),
            )
        return self.get_document(document["document_id"]) or dict(document)

    def get_document(self, document_id: str) -> dict | None:
        query = """
            SELECT document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, created_at, object_key
            FROM documents
            WHERE document_id = %s
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (document_id,))
            row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_document(row)

    def list_documents(self) -> list[dict]:
        query = """
            SELECT document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, created_at, object_key
            FROM documents
            ORDER BY created_at DESC
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return [_row_to_document(row) for row in rows]

    def set_status(self, document_id: str, status: str) -> dict | None:
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                "UPDATE documents SET status = %s WHERE document_id = %s",
                (status, document_id),
            )
        return self.get_document(document_id)

    def _ensure_schema(self):
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documents(
                    document_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    source_name TEXT,
                    tags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    object_key TEXT NOT NULL
                )
                """
            )

    def close(self):
        with self._lock:
            self._conn.close()


def _row_to_document(row: tuple) -> dict:
    return {
        "document_id": row[0],
        "file_name": row[1],
        "mime_type": row[2],
        "size_bytes": int(row[3]),
        "status": row[4],
        "source_name": row[5],
        "tags": json.loads(row[6] or "[]"),
        "created_at": row[7],
        "object_key": row[8],
    }
