from __future__ import annotations

from abc import ABC, abstractmethod


class DocumentStore(ABC):
    @abstractmethod
    def create_knowledge_base(self, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_knowledge_bases(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def create_document(self, document: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_document(self, document_id: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def list_documents(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def set_status(self, document_id: str, status: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, document_id: str) -> dict | None:
        raise NotImplementedError
