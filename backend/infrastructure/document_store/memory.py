from __future__ import annotations

from threading import RLock

from backend.infrastructure.document_store.base import DocumentStore
from backend.services.indexing_profiles import resolve_index_profile


class InMemoryDocumentStore(DocumentStore):
    def __init__(self):
        self._documents: dict[str, dict] = {}
        self._knowledge_bases: dict[str, dict] = {}
        self._lock = RLock()

    def create_knowledge_base(self, name: str) -> dict:
        with self._lock:
            record = self._knowledge_bases.get(name) or {
                "name": name,
                "created_at": None,
                **resolve_index_profile(),
            }
            self._knowledge_bases[name] = record
            return dict(record)

    def list_knowledge_bases(self) -> list[dict]:
        with self._lock:
            names = set(self._knowledge_bases.keys())
            for item in self._documents.values():
                knowledge_base = item.get("knowledge_base") or "default"
                names.add(knowledge_base)
            rows = []
            for name in sorted(names):
                record = self._knowledge_bases.get(name) or {"name": name, "created_at": None, **resolve_index_profile()}
                rows.append(dict(record))
            return rows

    def get_knowledge_base(self, name: str) -> dict | None:
        with self._lock:
            record = self._knowledge_bases.get(name)
            if record is not None:
                return dict(record)
            if any((item.get("knowledge_base") or "default") == name for item in self._documents.values()):
                return {"name": name, "created_at": None, **resolve_index_profile()}
            return None

    def rename_knowledge_base(self, current_name: str, new_name: str) -> dict | None:
        with self._lock:
            if current_name not in self._knowledge_bases and all(
                (item.get("knowledge_base") or "default") != current_name for item in self._documents.values()
            ):
                return None
            if new_name in self._knowledge_bases:
                raise ValueError(f"Knowledge base already exists: {new_name}")
            record = self._knowledge_bases.pop(current_name, {"name": current_name, "created_at": None})
            record["name"] = new_name
            self._knowledge_bases[new_name] = record
            for item in self._documents.values():
                if (item.get("knowledge_base") or "default") == current_name:
                    item["knowledge_base"] = new_name
            return dict(record)

    def update_knowledge_base(self, name: str, changes: dict) -> dict | None:
        with self._lock:
            record = self.get_knowledge_base(name)
            if record is None:
                return None
            record.update(changes)
            self._knowledge_bases[name] = dict(record)
            return dict(record)

    def delete_knowledge_base(self, name: str) -> dict | None:
        with self._lock:
            for item in self._documents.values():
                if (item.get("knowledge_base") or "default") == name:
                    raise ValueError(f"Knowledge base not empty: {name}")
            record = self._knowledge_bases.pop(name, None)
            return dict(record) if record is not None else None

    def create_document(self, document: dict) -> dict:
        with self._lock:
            knowledge_base = document.get("knowledge_base") or "default"
            self._knowledge_bases.setdefault(
                knowledge_base,
                {"name": knowledge_base, "created_at": None, **resolve_index_profile()},
            )
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
