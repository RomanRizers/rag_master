from __future__ import annotations

import json
from datetime import datetime
from threading import RLock

import psycopg

from backend.infrastructure.chat_store.base import ChatStore


class PostgresChatStore(ChatStore):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._lock = RLock()
        self._conn = psycopg.connect(dsn)
        self._conn.autocommit = True

    def create_session(self, session_id: str, created_at: str) -> dict:
        query = """
            INSERT INTO chat_sessions(session_id, created_at)
            VALUES (%s::uuid, %s::timestamptz)
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (session_id, created_at))
        return {"session_id": session_id, "created_at": _to_iso(created_at)}

    def list_sessions(self) -> list[dict]:
        query = """
            SELECT
                s.session_id,
                s.created_at,
                COUNT(m.message_id) AS message_count,
                MAX(m.created_at) AS last_message_at
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.session_id
            GROUP BY s.session_id, s.created_at
            ORDER BY s.created_at DESC
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return [
            {
                "session_id": str(row[0]),
                "created_at": _to_iso(row[1]),
                "message_count": int(row[2] or 0),
                "last_message_at": _to_iso(row[3]),
            }
            for row in rows
        ]

    def get_messages(self, session_id: str) -> list[dict] | None:
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM chat_sessions WHERE session_id = %s::uuid", (session_id,))
            if cursor.fetchone() is None:
                return None

            cursor.execute(
                """
                SELECT message_id, role, content, citations_json, created_at
                FROM chat_messages
                WHERE session_id = %s::uuid
                ORDER BY created_at ASC, message_id ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

        return [
            {
                "id": str(row[0]),
                "role": row[1],
                "content": row[2],
                "citations": _parse_json_value(row[3]),
                "created_at": _to_iso(row[4]),
            }
            for row in rows
        ]

    def append_message(self, session_id: str, message: dict) -> bool:
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM chat_sessions WHERE session_id = %s::uuid", (session_id,))
            if cursor.fetchone() is None:
                return False

            cursor.execute(
                """
                INSERT INTO chat_messages(
                    message_id, session_id, role, content, citations_json, created_at
                )
                VALUES (%s::uuid, %s::uuid, %s, %s, %s::jsonb, %s::timestamptz)
                """,
                (
                    message["id"],
                    session_id,
                    message["role"],
                    message["content"],
                    json.dumps(message.get("citations") or [], ensure_ascii=False),
                    message["created_at"],
                ),
            )
        return True

    def delete_session(self, session_id: str) -> dict | None:
        current = next((item for item in self.list_sessions() if item["session_id"] == session_id), None)
        if current is None:
            return None
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute("DELETE FROM chat_sessions WHERE session_id = %s::uuid", (session_id,))
        return current

    def close(self):
        with self._lock:
            self._conn.close()


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
