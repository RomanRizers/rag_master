from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from backend.infrastructure.document_store.base import DocumentStore


class SqliteDocumentStore(DocumentStore):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def create_document(self, document: dict) -> dict:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO documents(
                    document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, created_at, object_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
            self._conn.commit()
        return self.get_document(document["document_id"]) or dict(document)

    def get_document(self, document_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, created_at, object_key
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_document(row)

    def list_documents(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT document_id, file_name, mime_type, size_bytes, status, source_name, tags_json, created_at, object_key
                FROM documents
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [_row_to_document(row) for row in rows]

    def set_status(self, document_id: str, status: str) -> dict | None:
        with self._lock:
            self._conn.execute(
                "UPDATE documents SET status = ? WHERE document_id = ?",
                (status, document_id),
            )
            self._conn.commit()
        return self.get_document(document_id)

    def _ensure_schema(self):
        path = Path(self._db_path)
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._conn.execute(
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
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()


def _row_to_document(row: sqlite3.Row) -> dict:
    return {
        "document_id": row["document_id"],
        "file_name": row["file_name"],
        "mime_type": row["mime_type"],
        "size_bytes": int(row["size_bytes"]),
        "status": row["status"],
        "source_name": row["source_name"],
        "tags": json.loads(row["tags_json"] or "[]"),
        "created_at": row["created_at"],
        "object_key": row["object_key"],
    }
