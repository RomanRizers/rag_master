from __future__ import annotations

import io
import re
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

from backend.core.exceptions import ParsingError
from backend.ingestion.file_types import (
    DOCX_MIME_TYPES,
    MARKDOWN_MIME_TYPES,
    PDF_MIME_TYPES,
    TEXT_MIME_TYPES,
    normalize_mime_type,
)


def parse_document(
    file_name: str,
    mime_type: str,
    content: bytes,
    delimiters: list[str] | None = None,
) -> list[dict[str, Any]]:
    mime = normalize_mime_type(mime_type)
    if not content:
        raise ParsingError(message="Uploaded file is empty", code="empty_file")

    lower_name = file_name.lower()

    if mime in MARKDOWN_MIME_TYPES or lower_name.endswith(".md") or lower_name.endswith(".markdown"):
        return _parse_markdown(content, delimiters=delimiters)

    if mime in TEXT_MIME_TYPES or lower_name.endswith(".txt"):
        raw = content.decode("utf-8", errors="replace")
        if delimiters:
            segments = _split_by_delimiters(raw, delimiters)
            blocks = [
                {
                    "text": _normalize_text(seg),
                    "page": None,
                    "section": None,
                    "block_type": "paragraph",
                    "heading_level": None,
                    "heading_path": [],
                    "is_table_like": False,
                }
                for seg in segments
            ]
        else:
            blocks = [
                {
                    "text": _normalize_text(raw),
                    "page": None,
                    "section": None,
                    "block_type": "paragraph",
                    "heading_level": None,
                    "heading_path": [],
                    "is_table_like": False,
                }
            ]
        return _ensure_non_empty(blocks)

    if mime in DOCX_MIME_TYPES or lower_name.endswith(".docx"):
        return _parse_docx(content)

    if mime in PDF_MIME_TYPES or lower_name.endswith(".pdf"):
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
    heading_stack: list[str] = []

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
                heading_stack = heading_stack[: max(heading_level - 1, 0)]
                heading_stack.append(paragraph_text)
                blocks.append(
                    {
                        "text": paragraph_text,
                        "page": None,
                        "section": current_section,
                        "block_type": "heading",
                        "heading_level": heading_level,
                        "heading_path": list(heading_stack),
                        "is_table_like": False,
                    }
                )
                continue

            blocks.append(
                {
                    "text": paragraph_text,
                    "page": None,
                    "section": current_section,
                    "block_type": "paragraph",
                    "heading_level": None,
                    "heading_path": list(heading_stack),
                    "is_table_like": False,
                }
            )

        if tag == "tbl":
            rows = _extract_table_rows(element, namespace)
            for row in rows:
                if not row:
                    continue
                row_text = " | ".join(row)
                blocks.append(
                    {
                        "text": row_text,
                        "page": None,
                        "section": current_section,
                        "block_type": "table_row",
                        "heading_level": None,
                        "heading_path": list(heading_stack),
                        "is_table_like": True,
                    }
                )

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
            pages.append(
                {
                    "text": text,
                    "page": index,
                    "section": None,
                    "block_type": "paragraph",
                    "heading_level": None,
                    "heading_path": [],
                    "is_table_like": _looks_table_like(text),
                }
            )
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
        normalized_item.setdefault("block_type", "paragraph")
        normalized_item.setdefault("heading_level", None)
        normalized_item.setdefault("heading_path", [])
        normalized_item.setdefault("is_table_like", False)
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


def _looks_table_like(text: str) -> bool:
    separators = text.count("|") + text.count(";") + text.count("\t")
    digit_ratio = sum(char.isdigit() for char in text) / max(len(text), 1)
    return separators >= 3 or digit_ratio > 0.2


def _split_by_delimiters(text: str, delimiters: list[str]) -> list[str]:
    pattern = "|".join(re.escape(d) for d in sorted(delimiters, key=len, reverse=True))
    segments = re.split(pattern, text)
    return [seg.strip() for seg in segments if seg.strip()]


def _parse_markdown(content: bytes, delimiters: list[str] | None = None) -> list[dict[str, Any]]:
    text = content.decode("utf-8", errors="replace")
    segments = _split_by_delimiters(text, delimiters) if delimiters else [text]
    blocks: list[dict[str, Any]] = []
    for segment in segments:
        blocks.extend(_parse_markdown_segment(segment))
    return _ensure_non_empty(blocks)


_TABLE_ROWS_PER_CHUNK = 10  # header + this many data rows per table chunk


def _parse_markdown_segment(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    blocks: list[dict[str, Any]] = []
    heading_stack: list[str] = []
    current_section: str | None = None
    paragraph_buffer: list[str] = []
    table_buffer: list[str] = []  # raw pipe-table lines
    in_code_block = False

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        joined = " ".join(line for line in paragraph_buffer if line.strip())
        text_val = _normalize_text(joined)
        if text_val:
            blocks.append(
                {
                    "text": text_val,
                    "page": None,
                    "section": current_section,
                    "block_type": "paragraph",
                    "heading_level": None,
                    "heading_path": list(heading_stack),
                    "is_table_like": False,
                }
            )
        paragraph_buffer = []

    def flush_table() -> None:
        nonlocal table_buffer
        if not table_buffer:
            return
        _emit_markdown_table(table_buffer, blocks, current_section, heading_stack)
        table_buffer = []

    for line in lines:
        stripped = line.strip()

        # Toggle code block fence
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_table()
            in_code_block = not in_code_block
            paragraph_buffer.append(line)
            continue

        if in_code_block:
            paragraph_buffer.append(line)
            continue

        # ATX heading
        heading_match = re.match(r"^(#{1,6})\s+(.*\S)", line)
        if heading_match:
            flush_table()
            flush_paragraph()
            level = len(heading_match.group(1))
            heading_text = _normalize_text(heading_match.group(2))
            if heading_text:
                current_section = heading_text
                heading_stack = heading_stack[: level - 1]
                heading_stack.append(heading_text)
                blocks.append(
                    {
                        "text": heading_text,
                        "page": None,
                        "section": current_section,
                        "block_type": "heading",
                        "heading_level": level,
                        "heading_path": list(heading_stack),
                        "is_table_like": False,
                    }
                )
            continue

        # Pipe table row
        if _is_md_table_row(stripped):
            flush_paragraph()
            table_buffer.append(stripped)
            continue

        # Any other content ends an active table
        flush_table()

        if not stripped:
            flush_paragraph()
            continue

        paragraph_buffer.append(stripped)

    flush_table()
    flush_paragraph()
    return blocks


def _is_md_table_row(line: str) -> bool:
    return line.startswith("|") and line.count("|") >= 2


def _is_md_separator_row(line: str) -> bool:
    """Matches lines like |---|:---:|---| (GFM table separator)."""
    content = re.sub(r"[|\-: ]", "", line)
    return line.startswith("|") and content == ""


def _emit_markdown_table(
    raw_rows: list[str],
    blocks: list[dict[str, Any]],
    current_section: str | None,
    heading_stack: list[str],
) -> None:
    """Parse a collected pipe-table and emit chunks (header + N data rows each)."""
    # Separate header / separator / data rows
    non_sep = [r for r in raw_rows if not _is_md_separator_row(r)]
    if not non_sep:
        return

    header_row = non_sep[0]
    data_rows = non_sep[1:]

    if not data_rows:
        # Only a header — emit as-is
        blocks.append(
            {
                "text": header_row,
                "page": None,
                "section": current_section,
                "block_type": "table_row",
                "heading_level": None,
                "heading_path": list(heading_stack),
                "is_table_like": True,
            }
        )
        return

    # Emit groups: header + up to _TABLE_ROWS_PER_CHUNK data rows
    for i in range(0, len(data_rows), _TABLE_ROWS_PER_CHUNK):
        group = data_rows[i : i + _TABLE_ROWS_PER_CHUNK]
        table_text = "\n".join([header_row] + group)
        blocks.append(
            {
                "text": table_text,
                "page": None,
                "section": current_section,
                "block_type": "table_row",
                "heading_level": None,
                "heading_path": list(heading_stack),
                "is_table_like": True,
            }
        )
