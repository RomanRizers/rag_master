from __future__ import annotations

from dataclasses import dataclass

from backend.services.api_service import ApiService
from backend.services.chat_service import ChatService
from backend.services.document_service import DocumentService
from backend.services.health_service import HealthService
from backend.services.ingestion_service import IngestionService


@dataclass
class ApiServices:
    """Services for the CRUD API container (no LLM, no TextVectorizer)."""
    api_service: ApiService
    document_service: DocumentService
    ingestion_service: IngestionService
    health_service: HealthService

    def close(self):
        _safe_close(self.ingestion_service)
        _safe_close(self.document_service)


@dataclass
class ChatServices:
    """Services for the chat/search container (TextVectorizer + LLM)."""
    api_service: ApiService
    chat_service: ChatService

    def close(self):
        _safe_close(self.chat_service)


# Keep AppServices for backwards compatibility (tests, local dev)
@dataclass
class AppServices:
    api_service: ApiService
    chat_service: ChatService
    document_service: DocumentService
    ingestion_service: IngestionService
    health_service: HealthService

    def close(self):
        _safe_close(self.ingestion_service)
        _safe_close(self.chat_service)
        _safe_close(self.document_service)


def build_api_services() -> ApiServices:
    """Build services for the CRUD API container.

    TextVectorizer is NOT loaded here — ApiService uses it lazily,
    and the api container never calls search_query / index_documents.
    """
    api_service = ApiService()
    document_service = DocumentService()
    ingestion_service = IngestionService(
        document_service=document_service,
        api_service=api_service,
    )
    health_service = HealthService()
    return ApiServices(
        api_service=api_service,
        document_service=document_service,
        ingestion_service=ingestion_service,
        health_service=health_service,
    )


def build_chat_services() -> ChatServices:
    """Build services for the chat/search container (loads TextVectorizer + LLM)."""
    api_service = ApiService()
    chat_service = ChatService()
    return ChatServices(api_service=api_service, chat_service=chat_service)


def build_services() -> AppServices:
    """Build all services (monolith / local dev)."""
    api_service = ApiService()
    document_service = DocumentService()
    ingestion_service = IngestionService(
        document_service=document_service,
        api_service=api_service,
    )
    chat_service = ChatService()
    health_service = HealthService()
    return AppServices(
        api_service=api_service,
        chat_service=chat_service,
        document_service=document_service,
        ingestion_service=ingestion_service,
        health_service=health_service,
    )


def _safe_close(value):
    close_fn = getattr(value, "close", None)
    if callable(close_fn):
        close_fn()
