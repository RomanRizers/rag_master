from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from backend.core.exceptions import DocumentError


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
    content_bytes: bytes

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
    def __init__(self):
        self._documents: dict[str, StoredDocument] = {}
        self._lock = RLock()

    def create_document(
        self,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
        source_name: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        document_id = str(uuid4())
        record = StoredDocument(
            document_id=document_id,
            file_name=file_name,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=len(content_bytes),
            status="uploaded",
            source_name=source_name.strip() if isinstance(source_name, str) and source_name.strip() else None,
            tags=[tag.strip() for tag in (tags or []) if isinstance(tag, str) and tag.strip()],
            created_at=_now_iso(),
            content_bytes=content_bytes,
        )
        with self._lock:
            self._documents[document_id] = record
        return record.public_dict()

    def get_document(self, document_id: str) -> StoredDocument:
        with self._lock:
            record = self._documents.get(document_id)
            if record is None:
                raise DocumentError(
                    message=f"Document not found: {document_id}",
                    code="document_not_found",
                    status_code=404,
                )
            return record

    def list_documents(self) -> list[dict]:
        with self._lock:
            items = [record.public_dict() for record in self._documents.values()]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items

    def set_status(self, document_id: str, status: str):
        with self._lock:
            record = self._documents.get(document_id)
            if record is None:
                raise DocumentError(
                    message=f"Document not found: {document_id}",
                    code="document_not_found",
                    status_code=404,
                )
            record.status = status


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
