from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.core.config import Config
from backend.core.exceptions import DocumentError
from backend.core.exceptions import ValidationError
from backend.ingestion.file_types import resolve_upload_mime_type
from backend.infrastructure.document_store import DocumentStore, create_document_store
from backend.infrastructure.storage import StorageAdapter, create_storage_adapter

DEFAULT_KNOWLEDGE_BASE = "default"


@dataclass
class StoredDocument:
    document_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    status: str
    source_name: str | None
    tags: list[str]
    knowledge_base: str
    created_at: str
    object_key: str

    def public_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "source_name": self.source_name,
            "tags": list(self.tags),
            "knowledge_base": self.knowledge_base,
            "created_at": self.created_at,
        }


class DocumentService:
    def __init__(self, storage: StorageAdapter | None = None, store: DocumentStore | None = None):
        self.storage = storage or create_storage_adapter()
        self.store = store or create_document_store()

    def create_knowledge_base(self, name: str) -> dict:
        normalized = _normalize_knowledge_base(name)
        created = self.store.create_knowledge_base(
            {
                "name": normalized,
                "created_at": _now_iso(),
            }
        )
        counts = self._knowledge_base_document_counts()
        return _knowledge_base_public_dict(created["name"], created.get("created_at") or _now_iso(), counts)

    def create_document(
        self,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
        source_name: str | None = None,
        tags: list[str] | None = None,
        knowledge_base: str | None = None,
    ) -> dict:
        if len(content_bytes) > Config.MAX_UPLOAD_SIZE_BYTES:
            raise ValidationError(
                message=(
                    f"Uploaded file is too large: {len(content_bytes)} bytes; "
                    f"max allowed is {Config.MAX_UPLOAD_SIZE_BYTES} bytes"
                ),
                code="file_too_large",
                status_code=413,
            )

        resolved_mime = resolve_upload_mime_type(
            file_name=file_name,
            mime_type=mime_type,
            content=content_bytes,
        )
        if resolved_mime is None:
            raise DocumentError(
                message=f"Unsupported document type: {mime_type or 'unknown'}",
                code="invalid_file_type",
                status_code=400,
            )

        document_id = str(uuid4())
        object_key = f"{document_id}/{_safe_file_name(file_name)}"
        normalized_knowledge_base = _normalize_knowledge_base(knowledge_base)
        self.store.create_knowledge_base(
            {
                "name": normalized_knowledge_base,
                "created_at": _now_iso(),
            }
        )
        self.storage.save(object_key, content_bytes)
        record = StoredDocument(
            document_id=document_id,
            file_name=file_name,
            mime_type=resolved_mime,
            size_bytes=len(content_bytes),
            status="uploaded",
            source_name=source_name.strip() if isinstance(source_name, str) and source_name.strip() else None,
            tags=[tag.strip() for tag in (tags or []) if isinstance(tag, str) and tag.strip()],
            knowledge_base=normalized_knowledge_base,
            created_at=_now_iso(),
            object_key=object_key,
        )
        self.store.create_document(
            {
                "document_id": record.document_id,
                "file_name": record.file_name,
                "mime_type": record.mime_type,
                "size_bytes": record.size_bytes,
                "status": record.status,
                "source_name": record.source_name,
                "tags": list(record.tags),
                "knowledge_base": record.knowledge_base,
                "created_at": record.created_at,
                "object_key": record.object_key,
            }
        )
        return record.public_dict()

    def get_document(self, document_id: str) -> StoredDocument:
        record = self.store.get_document(document_id)
        if record is None:
            raise DocumentError(
                message=f"Document not found: {document_id}",
                code="document_not_found",
                status_code=404,
            )
        return StoredDocument(**record)

    def list_documents(self) -> list[dict]:
        items = [
            StoredDocument(**record).public_dict()
            for record in self.store.list_documents()
        ]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items

    def list_knowledge_bases(self) -> list[dict]:
        counts = self._knowledge_base_document_counts()
        items = []
        for item in self.store.list_knowledge_bases():
            name = _normalize_knowledge_base(item.get("name"))
            items.append(_knowledge_base_public_dict(name, item.get("created_at") or _now_iso(), counts))
        items.sort(key=lambda item: (item["created_at"], item["name"]), reverse=True)
        return items

    def rename_knowledge_base(self, current_name: str, new_name: str) -> dict:
        source_name = _normalize_knowledge_base(current_name)
        target_name = _normalize_knowledge_base(new_name)
        knowledge_bases = {item["name"]: item for item in self.store.list_knowledge_bases()}
        current = knowledge_bases.get(source_name)
        if current is None:
            raise DocumentError(
                message=f"Knowledge base not found: {source_name}",
                code="knowledge_base_not_found",
                status_code=404,
            )

        if source_name == target_name:
            return _knowledge_base_public_dict(source_name, current.get("created_at") or _now_iso(), self._knowledge_base_document_counts())

        self.store.create_knowledge_base(
            {
                "name": target_name,
                "created_at": current.get("created_at") or _now_iso(),
            }
        )
        for item in self.store.list_documents():
            if _normalize_knowledge_base(item.get("knowledge_base")) == source_name:
                self.store.update_document_knowledge_base(item["document_id"], target_name)
        self.store.delete_knowledge_base(source_name)
        created_at = knowledge_bases.get(target_name, {}).get("created_at") or current.get("created_at") or _now_iso()
        return _knowledge_base_public_dict(target_name, created_at, self._knowledge_base_document_counts())

    def delete_knowledge_base(self, name: str) -> dict:
        normalized = _normalize_knowledge_base(name)
        items = {item["name"]: item for item in self.store.list_knowledge_bases()}
        current = items.get(normalized)
        if current is None:
            raise DocumentError(
                message=f"Knowledge base not found: {normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        documents = [item for item in self.store.list_documents() if _normalize_knowledge_base(item.get("knowledge_base")) == normalized]
        if documents:
            raise ValidationError(
                message=f"Knowledge base '{normalized}' is not empty",
                code="knowledge_base_not_empty",
                status_code=409,
            )
        deleted = self.store.delete_knowledge_base(normalized)
        if deleted is None:
            raise DocumentError(
                message=f"Knowledge base not found: {normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        return _knowledge_base_public_dict(normalized, current.get("created_at") or _now_iso(), self._knowledge_base_document_counts())

    def move_documents_to_knowledge_base(self, document_ids: list[str], target_knowledge_base: str) -> list[dict]:
        normalized_target = _normalize_knowledge_base(target_knowledge_base)
        unique_ids: list[str] = []
        seen: set[str] = set()
        for document_id in document_ids:
            if isinstance(document_id, str) and document_id and document_id not in seen:
                unique_ids.append(document_id)
                seen.add(document_id)
        if not unique_ids:
            raise ValidationError(
                message="At least one document_id is required",
                code="document_ids_required",
                status_code=400,
            )
        self.store.create_knowledge_base({"name": normalized_target, "created_at": _now_iso()})
        updated_items: list[dict] = []
        for document_id in unique_ids:
            self.get_document(document_id)
            updated = self.store.update_document_knowledge_base(document_id, normalized_target)
            if updated is None:
                raise DocumentError(
                    message=f"Document not found: {document_id}",
                    code="document_not_found",
                    status_code=404,
                )
            updated_items.append(StoredDocument(**updated).public_dict())
        return updated_items

    def set_status(self, document_id: str, status: str):
        updated = self.store.set_status(document_id, status)
        if updated is None:
            raise DocumentError(
                message=f"Document not found: {document_id}",
                code="document_not_found",
                status_code=404,
            )

    def read_content(self, document_id: str) -> bytes:
        record = self.get_document(document_id)
        return self.storage.read(record.object_key)

    def delete_document(self, document_id: str) -> dict:
        record = self.get_document(document_id)
        self.storage.delete(record.object_key)
        deleted = self.store.delete_document(document_id)
        if deleted is None:
            raise DocumentError(
                message=f"Document not found: {document_id}",
                code="document_not_found",
                status_code=404,
            )
        return StoredDocument(**deleted).public_dict()

    def close(self):
        close_fn = getattr(self.store, "close", None)
        if callable(close_fn):
            close_fn()

    def _knowledge_base_document_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.store.list_documents():
            knowledge_base = _normalize_knowledge_base(item.get("knowledge_base"))
            counts[knowledge_base] = counts.get(knowledge_base, 0) + 1
        return counts


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_file_name(file_name: str) -> str:
    name = Path(file_name or "document.bin").name.strip()
    return name or "document.bin"


def _normalize_knowledge_base(value: str | None) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_KNOWLEDGE_BASE


def _knowledge_base_public_dict(name: str, created_at: str, counts: dict[str, int]) -> dict:
    return {
        "name": name,
        "created_at": created_at,
        "document_count": counts.get(name, 0),
    }
