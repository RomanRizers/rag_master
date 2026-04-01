from __future__ import annotations

import io
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

from backend.core.exceptions import ParsingError

DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
PDF_MIME_TYPES = {"application/pdf"}
TEXT_MIME_TYPES = {"text/plain"}


def parse_document(file_name: str, mime_type: str, content: bytes) -> list[dict[str, Any]]:
    mime = (mime_type or "").split(";")[0].strip().lower()
    if not content:
        raise ParsingError(message="Uploaded file is empty", code="empty_file")

    if mime in TEXT_MIME_TYPES or file_name.lower().endswith(".txt"):
        text = content.decode("utf-8", errors="replace").strip()
        return _ensure_non_empty([{"text": text, "page": None, "section": None}])

    if mime in DOCX_MIME_TYPES or file_name.lower().endswith(".docx"):
        return _parse_docx(content)

    if mime in PDF_MIME_TYPES or file_name.lower().endswith(".pdf"):
        return _parse_pdf(content)

    raise ParsingError(
        message=f"Unsupported document type: {mime_type or 'unknown'}",
        code="invalid_file_type",
        status_code=415,
    )


def _parse_docx(content: bytes) -> list[dict[str, Any]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except KeyError as exc:
        raise ParsingError(message="DOCX structure is invalid", code="parsing_failed") from exc
    except zipfile.BadZipFile as exc:
        raise ParsingError(message="DOCX file is corrupted", code="parsing_failed") from exc

    root = ET.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[dict[str, Any]] = []

    for paragraph in root.findall(".//w:p", namespace):
        text_nodes = paragraph.findall(".//w:t", namespace)
        text = "".join(node.text or "" for node in text_nodes).strip()
        if not text:
            continue
        paragraphs.append({"text": text, "page": None, "section": None})

    return _ensure_non_empty(paragraphs)


def _parse_pdf(content: bytes) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:
        raise ParsingError(
            message="PDF parsing requires optional dependency `pypdf`",
            code="parsing_failed",
            status_code=503,
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(content))
        pages: list[dict[str, Any]] = []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            pages.append({"text": text, "page": index, "section": None})
    except Exception as exc:
        raise ParsingError(message="Unable to parse PDF document", code="parsing_failed") from exc

    return _ensure_non_empty(pages)


def _ensure_non_empty(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [item for item in blocks if (item.get("text") or "").strip()]
    if not filtered:
        raise ParsingError(message="No readable text found in document", code="parsing_failed")
    return filtered
