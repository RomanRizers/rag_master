from __future__ import annotations

import io
import re
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
        text = _normalize_text(content.decode("utf-8", errors="replace"))
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
    blocks: list[dict[str, Any]] = []
    current_section: str | None = None

    body = root.find(".//w:body", namespace)
    if body is None:
        raise ParsingError(message="DOCX structure is invalid", code="parsing_failed")

    for element in body:
        tag = _local_name(element.tag)
        if tag == "p":
            paragraph_text = _extract_paragraph_text(element, namespace)
            if not paragraph_text:
                continue

            heading_level = _extract_heading_level(element, namespace)
            if heading_level is not None:
                current_section = paragraph_text
                blocks.append(
                    {
                        "text": f"[SECTION H{heading_level}] {paragraph_text}",
                        "page": None,
                        "section": current_section,
                    }
                )
                continue

            blocks.append({"text": paragraph_text, "page": None, "section": current_section})

        if tag == "tbl":
            rows = _extract_table_rows(element, namespace)
            for row in rows:
                if not row:
                    continue
                row_text = " | ".join(row)
                blocks.append({"text": f"[TABLE] {row_text}", "page": None, "section": current_section})

    return _ensure_non_empty(blocks)


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
            text = _normalize_text(page.extract_text() or "")
            if not text:
                continue
            pages.append({"text": text, "page": index, "section": None})
    except Exception as exc:
        raise ParsingError(message="Unable to parse PDF document", code="parsing_failed") from exc

    return _ensure_non_empty(pages)


def _ensure_non_empty(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = []
    for item in blocks:
        text = _normalize_text(item.get("text") or "")
        if not text:
            continue
        normalized_item = dict(item)
        normalized_item["text"] = text
        filtered.append(normalized_item)
    if not filtered:
        raise ParsingError(message="No readable text found in document", code="parsing_failed")
    return filtered


def _normalize_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", str(value or "")).strip()
    return collapsed


def _extract_paragraph_text(paragraph: ET.Element, namespace: dict[str, str]) -> str:
    text_nodes = paragraph.findall(".//w:t", namespace)
    raw_text = "".join(node.text or "" for node in text_nodes)
    return _normalize_text(raw_text)


def _extract_heading_level(paragraph: ET.Element, namespace: dict[str, str]) -> int | None:
    style = paragraph.find("./w:pPr/w:pStyle", namespace)
    if style is None:
        return None

    value = (
        style.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
        or style.get("w:val")
        or style.get("val")
        or ""
    ).strip()
    if not value.lower().startswith("heading"):
        return None

    level_part = value[len("heading") :]
    if level_part.isdigit():
        return int(level_part)
    return 1


def _extract_table_rows(table: ET.Element, namespace: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall("./w:tr", namespace):
        cells: list[str] = []
        for cell in row.findall("./w:tc", namespace):
            cell_text_fragments: list[str] = []
            for paragraph in cell.findall(".//w:p", namespace):
                paragraph_text = _extract_paragraph_text(paragraph, namespace)
                if paragraph_text:
                    cell_text_fragments.append(paragraph_text)
            cell_text = _normalize_text(" ".join(cell_text_fragments))
            if cell_text:
                cells.append(cell_text)
        rows.append(cells)
    return rows


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", maxsplit=1)[1]
    return tag
