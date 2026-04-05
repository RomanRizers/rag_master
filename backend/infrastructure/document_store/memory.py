from __future__ import annotations

from threading import RLock

from backend.infrastructure.document_store.base import DocumentStore


class InMemoryDocumentStore(DocumentStore):
    def __init__(self):
        self._documents: dict[str, dict] = {}
        self._lock = RLock()

    def create_document(self, document: dict) -> dict:
        with self._lock:
            self._documents[document["document_id"]] = dict(document)
            return dict(self._documents[document["document_id"]])

    def get_document(self, document_id: str) -> dict | None:
        with self._lock:
            record = self._documents.get(document_id)
            return dict(record) if record is not None else None

    def list_documents(self) -> list[dict]:
        with self._lock:
            return [dict(item) for item in self._documents.values()]

    def set_status(self, document_id: str, status: str) -> dict | None:
        with self._lock:
            record = self._documents.get(document_id)
            if record is None:
                return None
            record["status"] = status
            return dict(record)

    def delete_document(self, document_id: str) -> dict | None:
        with self._lock:
            record = self._documents.pop(document_id, None)
            return dict(record) if record is not None else None
