from __future__ import annotations

from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    @abstractmethod
    def save(self, object_key: str, content: bytes) -> None:
        """Persist binary content by object key."""

    @abstractmethod
    def read(self, object_key: str) -> bytes:
        """Read binary content by object key."""
