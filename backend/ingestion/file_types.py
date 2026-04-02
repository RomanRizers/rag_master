from __future__ import annotations

from pathlib import Path

DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
PDF_MIME_TYPES = {"application/pdf"}
TEXT_MIME_TYPES = {"text/plain"}

SUPPORTED_EXTENSIONS = {".txt", ".docx", ".pdf"}


def normalize_mime_type(mime_type: str) -> str:
    return (mime_type or "").split(";", 1)[0].strip().lower()


def is_supported_document_type(file_name: str, mime_type: str) -> bool:
    mime = normalize_mime_type(mime_type)
    suffix = Path(file_name or "").suffix.lower().strip()
    return (
        mime in TEXT_MIME_TYPES
        or mime in DOCX_MIME_TYPES
        or mime in PDF_MIME_TYPES
        or suffix in SUPPORTED_EXTENSIONS
    )
