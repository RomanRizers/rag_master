from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.core.exceptions import DocumentError
from backend.ingestion.file_types import is_supported_document_type
from backend.infrastructure.document_store import DocumentStore, create_document_store
from backend.infrastructure.storage import StorageAdapter, create_storage_adapter


@dataclass
class StoredDocument:
    document_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    status: str
    source_name: str | None
    tags: list[str]
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
    ) -> dict:
        if not is_supported_document_type(file_name=file_name, mime_type=mime_type):
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
            mime_type=mime_type or "application/octet-stream",
            size_bytes=len(content_bytes),
            status="uploaded",
            source_name=source_name.strip() if isinstance(source_name, str) and source_name.strip() else None,
            tags=[tag.strip() for tag in (tags or []) if isinstance(tag, str) and tag.strip()],
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

    def close(self):
        close_fn = getattr(self.store, "close", None)
        if callable(close_fn):
            close_fn()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_file_name(file_name: str) -> str:
    name = Path(file_name or "document.bin").name.strip()
    return name or "document.bin"
