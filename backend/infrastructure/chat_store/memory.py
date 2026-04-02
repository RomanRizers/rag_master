from __future__ import annotations

from threading import RLock

from backend.infrastructure.chat_store.base import ChatStore


class InMemoryChatStore(ChatStore):
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._messages: dict[str, list[dict]] = {}
        self._lock = RLock()

    def create_session(self, session_id: str, created_at: str) -> dict:
        with self._lock:
            self._sessions[session_id] = {"session_id": session_id, "created_at": created_at}
            self._messages[session_id] = []
            return dict(self._sessions[session_id])

    def list_sessions(self) -> list[dict]:
        with self._lock:
            items = []
            for session_id, meta in self._sessions.items():
                history = self._messages.get(session_id, [])
                last_message_at = history[-1]["created_at"] if history else None
                items.append(
                    {
                        "session_id": session_id,
                        "created_at": meta["created_at"],
                        "message_count": len(history),
                        "last_message_at": last_message_at,
                    }
                )
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items

    def get_messages(self, session_id: str) -> list[dict] | None:
        with self._lock:
            messages = self._messages.get(session_id)
            if messages is None:
                return None
            return list(messages)

    def append_message(self, session_id: str, message: dict) -> bool:
        with self._lock:
            messages = self._messages.get(session_id)
            if messages is None:
                return False
            messages.append(dict(message))
            return True
