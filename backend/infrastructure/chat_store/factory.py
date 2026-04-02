from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.chat_store.base import ChatStore
from backend.infrastructure.chat_store.memory import InMemoryChatStore
from backend.infrastructure.chat_store.postgres import PostgresChatStore


def create_chat_store() -> ChatStore:
    backend = Config.CHAT_STORE_BACKEND
    if backend == "memory":
        return InMemoryChatStore()
    if backend == "postgres":
        if not Config.POSTGRES_DSN:
            raise ValidationError(
                message="POSTGRES_DSN is required when CHAT_STORE_BACKEND=postgres",
                code="invalid_chat_store_config",
            )
        return PostgresChatStore(dsn=Config.POSTGRES_DSN)
    raise ValidationError(
        message=f"Unsupported chat store backend: {backend}",
        code="invalid_chat_store_backend",
    )
