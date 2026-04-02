from __future__ import annotations

import io
from pathlib import Path
import string
import zipfile

DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
PDF_MIME_TYPES = {"application/pdf"}
TEXT_MIME_TYPES = {"text/plain"}

SUPPORTED_EXTENSIONS = {".txt", ".docx", ".pdf"}


def normalize_mime_type(mime_type: str) -> str:
    return (mime_type or "").split(";", 1)[0].strip().lower()


def is_supported_document_type(file_name: str, mime_type: str, content: bytes | None = None) -> bool:
    if content is None:
        mime = normalize_mime_type(mime_type)
        suffix = Path(file_name or "").suffix.lower().strip()
        return (
            mime in TEXT_MIME_TYPES
            or mime in DOCX_MIME_TYPES
            or mime in PDF_MIME_TYPES
            or suffix in SUPPORTED_EXTENSIONS
        )
    return resolve_upload_mime_type(file_name=file_name, mime_type=mime_type, content=content) is not None


def resolve_upload_mime_type(file_name: str, mime_type: str, content: bytes) -> str | None:
    declared_kind = _declared_kind(file_name=file_name, mime_type=mime_type)
    if declared_kind is None:
        return None
    sniffed_kind = _sniff_kind(content)
    if sniffed_kind is None:
        return None
    if declared_kind != sniffed_kind:
        return None
    return _kind_to_mime(sniffed_kind)


def _declared_kind(file_name: str, mime_type: str) -> str | None:
    mime = normalize_mime_type(mime_type)
    suffix = Path(file_name or "").suffix.lower().strip()
    mime_kind = _mime_to_kind(mime)
    ext_kind = _extension_to_kind(suffix)
    if mime_kind and ext_kind and mime_kind != ext_kind:
        return None
    return mime_kind or ext_kind


def _sniff_kind(content: bytes) -> str | None:
    if _looks_like_pdf(content):
        return "pdf"
    if _looks_like_docx(content):
        return "docx"
    if _looks_like_text(content):
        return "txt"
    return None


def _looks_like_pdf(content: bytes) -> bool:
    return bytes(content[:5]) == b"%PDF-"


def _looks_like_docx(content: bytes) -> bool:
    if not zipfile.is_zipfile(io.BytesIO(content)):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
        return "word/document.xml" in names and "[Content_Types].xml" in names
    except Exception:
        return False


def _looks_like_text(content: bytes) -> bool:
    if not content:
        return False
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False

    sample = text[:2048]
    if not sample:
        return False
    printable = sum(1 for ch in sample if ch in string.printable or ch.isspace())
    return printable / len(sample) >= 0.95


def _kind_to_mime(kind: str) -> str:
    if kind == "pdf":
        return "application/pdf"
    if kind == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "text/plain"


def _mime_to_kind(mime: str) -> str | None:
    if mime in PDF_MIME_TYPES:
        return "pdf"
    if mime in DOCX_MIME_TYPES:
        return "docx"
    if mime in TEXT_MIME_TYPES:
        return "txt"
    return None


def _extension_to_kind(suffix: str) -> str | None:
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix == ".txt":
        return "txt"
    return None
