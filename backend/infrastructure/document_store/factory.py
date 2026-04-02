from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.document_store.base import DocumentStore
from backend.infrastructure.document_store.memory import InMemoryDocumentStore
from backend.infrastructure.document_store.postgres import PostgresDocumentStore


def create_document_store() -> DocumentStore:
    backend = Config.DOCUMENT_STORE_BACKEND
    if backend == "memory":
        return InMemoryDocumentStore()
    if backend == "postgres":
        if not Config.POSTGRES_DSN:
            raise ValidationError(
                message="POSTGRES_DSN is required when DOCUMENT_STORE_BACKEND=postgres",
                code="invalid_document_store_config",
            )
        return PostgresDocumentStore(dsn=Config.POSTGRES_DSN)
    raise ValidationError(
        message=f"Unsupported document store backend: {backend}",
        code="invalid_document_store_backend",
    )
