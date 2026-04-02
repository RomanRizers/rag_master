from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from backend.infrastructure.chat_store.base import ChatStore


class SqliteChatStore(ChatStore):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def create_session(self, session_id: str, created_at: str) -> dict:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO chat_sessions(session_id, created_at)
                VALUES (?, ?)
                """,
                (session_id, created_at),
            )
            self._conn.commit()
        return {"session_id": session_id, "created_at": created_at}

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
        with self._lock:
            rows = self._conn.execute(query).fetchall()
        return [
            {
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "message_count": int(row["message_count"] or 0),
                "last_message_at": row["last_message_at"],
            }
            for row in rows
        ]

    def get_messages(self, session_id: str) -> list[dict] | None:
        with self._lock:
            session = self._conn.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                return None
            rows = self._conn.execute(
                """
                SELECT message_id, role, content, citations_json, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC, message_id ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "id": row["message_id"],
                "role": row["role"],
                "content": row["content"],
                "citations": json.loads(row["citations_json"] or "[]"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def append_message(self, session_id: str, message: dict) -> bool:
        with self._lock:
            session = self._conn.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                return False

            self._conn.execute(
                """
                INSERT INTO chat_messages(
                    message_id, session_id, role, content, citations_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
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
            self._conn.commit()
        return True

    def _ensure_schema(self):
        path = Path(self._db_path)
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions(
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages(
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created "
                "ON chat_messages(session_id, created_at)"
            )
            self._conn.commit()
