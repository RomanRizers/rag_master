from __future__ import annotations

import json
from datetime import datetime
from threading import RLock

import psycopg

from backend.infrastructure.document_store.base import DocumentStore
from backend.services.indexing_profiles import resolve_index_profile


class PostgresDocumentStore(DocumentStore):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._lock = RLock()
        self._conn = psycopg.connect(dsn)
        self._conn.autocommit = True

    def create_document(self, document: dict) -> dict:
        self.create_knowledge_base(document.get("knowledge_base") or "default")
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

    def create_knowledge_base(self, name: str) -> dict:
        defaults = resolve_index_profile()
        query = """
            INSERT INTO knowledge_bases(
                name, profile_mode, chunk_size_tokens, chunk_overlap_tokens, chunk_keyword_limit, document_keyword_limit
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING name, created_at, profile_mode, chunk_size_tokens, chunk_overlap_tokens, chunk_keyword_limit, document_keyword_limit
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                query,
                (
                    name,
                    defaults["profile_mode"],
                    defaults["chunk_size_tokens"],
                    defaults["chunk_overlap_tokens"],
                    defaults["chunk_keyword_limit"],
                    defaults["document_keyword_limit"],
                ),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    """
                    SELECT name, created_at, profile_mode, chunk_size_tokens, chunk_overlap_tokens, chunk_keyword_limit, document_keyword_limit
                    FROM knowledge_bases WHERE name = %s
                    """,
                    (name,),
                )
                row = cursor.fetchone()
        return _row_to_knowledge_base(row)

    def list_knowledge_bases(self) -> list[dict]:
        query = """
            SELECT
                kb.name,
                kb.created_at,
                kb.profile_mode,
                kb.chunk_size_tokens,
                kb.chunk_overlap_tokens,
                kb.chunk_keyword_limit,
                kb.document_keyword_limit,
                COUNT(d.document_id) AS document_count
            FROM knowledge_bases kb
            LEFT JOIN documents d ON d.knowledge_base = kb.name
            GROUP BY
                kb.name,
                kb.created_at,
                kb.profile_mode,
                kb.chunk_size_tokens,
                kb.chunk_overlap_tokens,
                kb.chunk_keyword_limit,
                kb.document_keyword_limit
            ORDER BY kb.name ASC
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        items = []
        for row in rows:
            item = _row_to_knowledge_base(row[:7])
            item["document_count"] = int(row[7] or 0)
            items.append(item)
        return items

    def get_knowledge_base(self, name: str) -> dict | None:
        query = """
            SELECT name, created_at, profile_mode, chunk_size_tokens, chunk_overlap_tokens, chunk_keyword_limit, document_keyword_limit
            FROM knowledge_bases
            WHERE name = %s
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (name,))
            row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_knowledge_base(row)

    def rename_knowledge_base(self, current_name: str, new_name: str) -> dict | None:
        with self._lock, self._conn.transaction(), self._conn.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM knowledge_bases WHERE name = %s",
                (current_name,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                "SELECT name FROM knowledge_bases WHERE name = %s",
                (new_name,),
            )
            if cursor.fetchone() is not None:
                raise psycopg.errors.UniqueViolation(f"Knowledge base already exists: {new_name}")
            cursor.execute(
                "UPDATE knowledge_bases SET name = %s WHERE name = %s",
                (new_name, current_name),
            )
            cursor.execute(
                "UPDATE documents SET knowledge_base = %s WHERE knowledge_base = %s",
                (new_name, current_name),
            )
        return self.get_knowledge_base(new_name)

    def update_knowledge_base(self, name: str, changes: dict) -> dict | None:
        allowed_fields = {
            "profile_mode",
            "chunk_size_tokens",
            "chunk_overlap_tokens",
            "chunk_keyword_limit",
            "document_keyword_limit",
        }
        update_fields = [(key, value) for key, value in changes.items() if key in allowed_fields]
        if not update_fields:
            return self.get_knowledge_base(name)
        assignments = ", ".join(f"{field} = %s" for field, _ in update_fields)
        params = [value for _, value in update_fields] + [name]
        query = f"UPDATE knowledge_bases SET {assignments} WHERE name = %s"
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.rowcount == 0:
                return None
        return self.get_knowledge_base(name)

    def delete_knowledge_base(self, name: str) -> dict | None:
        with self._lock, self._conn.transaction(), self._conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM documents WHERE knowledge_base = %s",
                (name,),
            )
            if int((cursor.fetchone() or [0])[0] or 0) > 0:
                raise psycopg.errors.CheckViolation(f"Knowledge base not empty: {name}")
            cursor.execute(
                "DELETE FROM knowledge_bases WHERE name = %s RETURNING name",
                (name,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {"name": row[0]}

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
    defaults = resolve_index_profile(
        row[2] if len(row) > 2 else None,
        chunk_size_tokens=row[3] if len(row) > 3 else None,
        chunk_overlap_tokens=row[4] if len(row) > 4 else None,
        chunk_keyword_limit=row[5] if len(row) > 5 else None,
        document_keyword_limit=row[6] if len(row) > 6 else None,
    )
    return {
        "name": row[0],
        "created_at": _to_iso(row[1] if len(row) > 1 else None),
        "profile_mode": defaults["profile_mode"],
        "chunk_size_tokens": int(defaults["chunk_size_tokens"]),
        "chunk_overlap_tokens": int(defaults["chunk_overlap_tokens"]),
        "chunk_keyword_limit": int(defaults["chunk_keyword_limit"]),
        "document_keyword_limit": int(defaults["document_keyword_limit"]),
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
