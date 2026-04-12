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
from backend.services.indexing_profiles import resolve_index_profile

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
        self.storage.save(object_key, content_bytes)
        record = StoredDocument(
            document_id=document_id,
            file_name=file_name,
            mime_type=resolved_mime,
            size_bytes=len(content_bytes),
            status="uploaded",
            source_name=source_name.strip() if isinstance(source_name, str) and source_name.strip() else None,
            tags=[tag.strip() for tag in (tags or []) if isinstance(tag, str) and tag.strip()],
            knowledge_base=_normalize_knowledge_base(knowledge_base),
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
        counts: dict[str, int] = {}
        for item in self.store.list_documents():
            knowledge_base = _normalize_knowledge_base(item.get("knowledge_base"))
            counts[knowledge_base] = counts.get(knowledge_base, 0) + 1

        items: dict[str, dict] = {}
        for item in self.store.list_knowledge_bases():
            knowledge_base = _normalize_knowledge_base(item.get("name"))
            items[knowledge_base] = self._serialize_knowledge_base(
                {
                    **resolve_index_profile(
                        item.get("profile_mode"),
                        chunk_size_tokens=item.get("chunk_size_tokens"),
                        chunk_overlap_tokens=item.get("chunk_overlap_tokens"),
                        chunk_keyword_limit=item.get("chunk_keyword_limit"),
                        document_keyword_limit=item.get("document_keyword_limit"),
                    ),
                    "name": knowledge_base,
                    "created_at": item.get("created_at"),
                    "document_count": int(item.get("document_count") or 0),
                }
            )
            counts.setdefault(knowledge_base, int(item.get("document_count") or 0))

        for knowledge_base, count in counts.items():
            if knowledge_base not in items:
                items[knowledge_base] = self._serialize_knowledge_base(
                    {
                        **resolve_index_profile(),
                        "name": knowledge_base,
                        "created_at": None,
                        "document_count": count,
                    }
                )
            else:
                items[knowledge_base]["document_count"] = count

        return [items[name] for name in sorted(items.keys())]

    def create_knowledge_base(self, name: str) -> dict:
        normalized = _normalize_knowledge_base(name)
        existing_names = {item["name"] for item in self.list_knowledge_bases()}
        if normalized in existing_names:
            raise ValidationError(
                message=f"Knowledge base already exists: {normalized}",
                code="knowledge_base_exists",
                status_code=409,
            )
        created = self.store.create_knowledge_base(normalized)
        return self._serialize_knowledge_base({**created, "document_count": 0})

    def get_knowledge_base(self, name: str) -> dict:
        normalized = _normalize_knowledge_base(name)
        record = self.store.get_knowledge_base(normalized)
        if record is None:
            raise DocumentError(
                message=f"Knowledge base not found: {normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        count = sum(
            1 for item in self.store.list_documents() if _normalize_knowledge_base(item.get("knowledge_base")) == normalized
        )
        return self._serialize_knowledge_base({**record, "document_count": count})

    def rename_knowledge_base(self, current_name: str, new_name: str) -> dict:
        current_normalized = _normalize_knowledge_base(current_name)
        next_normalized = _normalize_knowledge_base(new_name)
        items = self.list_knowledge_bases()
        counts = {item["name"]: int(item.get("document_count") or 0) for item in items}
        if current_normalized not in counts:
            raise DocumentError(
                message=f"Knowledge base not found: {current_normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        if next_normalized != current_normalized and next_normalized in counts:
            raise ValidationError(
                message=f"Knowledge base already exists: {next_normalized}",
                code="knowledge_base_exists",
                status_code=409,
            )
        if next_normalized == current_normalized:
            return self.get_knowledge_base(current_normalized)
        renamed = self.store.rename_knowledge_base(current_normalized, next_normalized)
        if renamed is None:
            raise DocumentError(
                message=f"Knowledge base not found: {current_normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        return self._serialize_knowledge_base({**renamed, "document_count": counts[current_normalized]})

    def update_knowledge_base(
        self,
        name: str,
        *,
        profile_mode: str | None = None,
        chunk_size_tokens: int | None = None,
        chunk_overlap_tokens: int | None = None,
        chunk_keyword_limit: int | None = None,
        document_keyword_limit: int | None = None,
    ) -> dict:
        normalized = _normalize_knowledge_base(name)
        current = self.store.get_knowledge_base(normalized)
        if current is None:
            raise DocumentError(
                message=f"Knowledge base not found: {normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        resolved = resolve_index_profile(
            profile_mode or current.get("profile_mode"),
            chunk_size_tokens=chunk_size_tokens if chunk_size_tokens is not None else current.get("chunk_size_tokens"),
            chunk_overlap_tokens=chunk_overlap_tokens if chunk_overlap_tokens is not None else current.get("chunk_overlap_tokens"),
            chunk_keyword_limit=chunk_keyword_limit if chunk_keyword_limit is not None else current.get("chunk_keyword_limit"),
            document_keyword_limit=document_keyword_limit if document_keyword_limit is not None else current.get("document_keyword_limit"),
        )
        updated = self.store.update_knowledge_base(normalized, resolved)
        if updated is None:
            raise DocumentError(
                message=f"Knowledge base not found: {normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        count = sum(
            1 for item in self.store.list_documents() if _normalize_knowledge_base(item.get("knowledge_base")) == normalized
        )
        return self._serialize_knowledge_base({**updated, "document_count": count})

    def delete_knowledge_base(self, name: str) -> dict:
        normalized = _normalize_knowledge_base(name)
        counts = {item["name"]: int(item.get("document_count") or 0) for item in self.list_knowledge_bases()}
        if normalized not in counts:
            raise DocumentError(
                message=f"Knowledge base not found: {normalized}",
                code="knowledge_base_not_found",
                status_code=404,
            )
        if counts[normalized] > 0:
            raise ValidationError(
                message=f"Knowledge base is not empty: {normalized}",
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
        return self._serialize_knowledge_base(
            {
                **resolve_index_profile(),
                "name": normalized,
                "created_at": None,
                "document_count": 0,
            }
        )

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

    @staticmethod
    def _serialize_knowledge_base(item: dict) -> dict:
        resolved = resolve_index_profile(
            item.get("profile_mode"),
            chunk_size_tokens=item.get("chunk_size_tokens"),
            chunk_overlap_tokens=item.get("chunk_overlap_tokens"),
            chunk_keyword_limit=item.get("chunk_keyword_limit"),
            document_keyword_limit=item.get("document_keyword_limit"),
        )
        return {
            "name": _normalize_knowledge_base(item.get("name")),
            "document_count": int(item.get("document_count") or 0),
            "created_at": item.get("created_at"),
            "profile_mode": str(resolved["profile_mode"]),
            "chunk_size_tokens": int(resolved["chunk_size_tokens"]),
            "chunk_overlap_tokens": int(resolved["chunk_overlap_tokens"]),
            "chunk_keyword_limit": int(resolved["chunk_keyword_limit"]),
            "document_keyword_limit": int(resolved["document_keyword_limit"]),
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_file_name(file_name: str) -> str:
    name = Path(file_name or "document.bin").name.strip()
    return name or "document.bin"


def _normalize_knowledge_base(value: str | None) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_KNOWLEDGE_BASE
