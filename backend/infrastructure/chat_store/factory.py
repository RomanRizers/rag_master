from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.chat_store.base import ChatStore
from backend.infrastructure.chat_store.memory import InMemoryChatStore
from backend.infrastructure.chat_store.sqlite import SqliteChatStore


def create_chat_store() -> ChatStore:
    backend = Config.CHAT_STORE_BACKEND
    if backend == "memory":
        return InMemoryChatStore()
    if backend == "sqlite":
        if not Config.CHAT_SQLITE_PATH:
            raise ValidationError(
                message="CHAT_SQLITE_PATH is required when CHAT_STORE_BACKEND=sqlite",
                code="invalid_chat_store_config",
            )
        return SqliteChatStore(db_path=Config.CHAT_SQLITE_PATH)
    raise ValidationError(
        message=f"Unsupported chat store backend: {backend}",
        code="invalid_chat_store_backend",
    )
