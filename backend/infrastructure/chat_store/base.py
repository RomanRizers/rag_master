from __future__ import annotations

from abc import ABC, abstractmethod


class ChatStore(ABC):
    @abstractmethod
    def create_session(self, session_id: str, created_at: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, session_id: str) -> list[dict] | None:
        raise NotImplementedError

    @abstractmethod
    def append_message(self, session_id: str, message: dict) -> bool:
        raise NotImplementedError
