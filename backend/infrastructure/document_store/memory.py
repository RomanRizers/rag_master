from __future__ import annotations

from threading import RLock

from backend.infrastructure.document_store.base import DocumentStore


class InMemoryDocumentStore(DocumentStore):
    def __init__(self):
        self._documents: dict[str, dict] = {}
        self._knowledge_bases: dict[str, dict] = {}
        self._lock = RLock()

    def create_knowledge_base(self, name: str) -> dict:
        with self._lock:
            record = self._knowledge_bases.get(name) or {"name": name, "created_at": None}
            self._knowledge_bases[name] = record
            return dict(record)

    def list_knowledge_bases(self) -> list[dict]:
        with self._lock:
            names = set(self._knowledge_bases.keys())
            for item in self._documents.values():
                knowledge_base = item.get("knowledge_base") or "default"
                names.add(knowledge_base)
            return [{"name": name} for name in sorted(names)]

    def create_document(self, document: dict) -> dict:
        with self._lock:
            knowledge_base = document.get("knowledge_base") or "default"
            self._knowledge_bases.setdefault(knowledge_base, {"name": knowledge_base, "created_at": None})
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
