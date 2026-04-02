from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.document_store.base import DocumentStore
from backend.infrastructure.document_store.memory import InMemoryDocumentStore
from backend.infrastructure.document_store.sqlite import SqliteDocumentStore


def create_document_store() -> DocumentStore:
    backend = Config.DOCUMENT_STORE_BACKEND
    if backend == "memory":
        return InMemoryDocumentStore()
    if backend == "sqlite":
        if not Config.DOCUMENT_SQLITE_PATH:
            raise ValidationError(
                message="DOCUMENT_SQLITE_PATH is required when DOCUMENT_STORE_BACKEND=sqlite",
                code="invalid_document_store_config",
            )
        return SqliteDocumentStore(db_path=Config.DOCUMENT_SQLITE_PATH)
    raise ValidationError(
        message=f"Unsupported document store backend: {backend}",
        code="invalid_document_store_backend",
    )
