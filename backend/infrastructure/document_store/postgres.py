from __future__ import annotations

import json
from datetime import datetime
from threading import RLock

import psycopg

from backend.infrastructure.document_store.base import DocumentStore


class PostgresDocumentStore(DocumentStore):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._lock = RLock()
        self._conn = psycopg.connect(dsn)
        self._conn.autocommit = True

    def create_document(self, document: dict) -> dict:
        query = """
            INSERT INTO documents(
                document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, knowledge_base, created_at, object_key
            )
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::timestamptz, %s)
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
                    document.get("knowledge_base") or "default",
                    document["created_at"],
                    document["object_key"],
                ),
            )
        return self.get_document(document["document_id"]) or dict(document)

    def get_document(self, document_id: str) -> dict | None:
        query = """
            SELECT document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, knowledge_base, created_at, object_key
            FROM documents
            WHERE document_id = %s::uuid
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (document_id,))
            row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_document(row)

    def list_documents(self) -> list[dict]:
        query = """
            SELECT document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, knowledge_base, created_at, object_key
            FROM documents
            ORDER BY created_at DESC
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return [_row_to_document(row) for row in rows]

    def create_knowledge_base(self, knowledge_base: dict) -> dict:
        query = """
            INSERT INTO knowledge_bases(name, created_at)
            VALUES (%s, %s::timestamptz)
            ON CONFLICT (name) DO UPDATE
            SET created_at = LEAST(knowledge_bases.created_at, EXCLUDED.created_at)
            RETURNING name, created_at
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (knowledge_base["name"], knowledge_base["created_at"]))
            row = cursor.fetchone()
        return _row_to_knowledge_base(row) if row is not None else dict(knowledge_base)

    def list_knowledge_bases(self) -> list[dict]:
        query = """
            SELECT name, created_at
            FROM knowledge_bases
            ORDER BY created_at DESC, name ASC
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return [_row_to_knowledge_base(row) for row in rows]

    def update_document_knowledge_base(self, document_id: str, knowledge_base: str) -> dict | None:
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                "UPDATE documents SET knowledge_base = %s WHERE document_id = %s::uuid",
                (knowledge_base, document_id),
            )
        return self.get_document(document_id)

    def delete_knowledge_base(self, name: str) -> dict | None:
        current = next((item for item in self.list_knowledge_bases() if item["name"] == name), None)
        if current is None:
            return None
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute("DELETE FROM knowledge_bases WHERE name = %s", (name,))
        return current

    def set_status(self, document_id: str, status: str) -> dict | None:
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                "UPDATE documents SET status = %s WHERE document_id = %s::uuid",
                (status, document_id),
            )
        return self.get_document(document_id)

    def delete_document(self, document_id: str) -> dict | None:
        current = self.get_document(document_id)
        if current is None:
            return None
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE document_id = %s::uuid", (document_id,))
        return current

    def close(self):
        with self._lock:
            self._conn.close()


def _row_to_document(row: tuple) -> dict:
    return {
        "document_id": str(row[0]),
        "file_name": row[1],
        "mime_type": row[2],
        "size_bytes": int(row[3]),
        "status": row[4],
        "source_name": row[5],
        "tags": _parse_json_value(row[6]),
        "knowledge_base": row[7] or "default",
        "created_at": _to_iso(row[8]),
        "object_key": row[9],
    }


def _row_to_knowledge_base(row: tuple) -> dict:
    return {
        "name": row[0],
        "created_at": _to_iso(row[1]),
    }


def _to_iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_json_value(value):
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        return json.loads(value or "[]")
    return value
