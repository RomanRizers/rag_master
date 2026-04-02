from __future__ import annotations

from dataclasses import dataclass

from backend.services.api_service import ApiService
from backend.services.chat_service import ChatService
from backend.services.document_service import DocumentService
from backend.services.health_service import HealthService
from backend.services.ingestion_service import IngestionService


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


def build_services() -> AppServices:
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
