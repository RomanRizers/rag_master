from __future__ import annotations

from typing import Any


def chunk_blocks(
    blocks: list[dict[str, Any]],
    chunk_size_chars: int = 1200,
    chunk_overlap_chars: int = 180,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    chunk_index = 0

    for block in blocks:
        text = str(block.get("text") or "").strip()
        if not text:
            continue

        page = block.get("page")
        section = block.get("section")
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size_chars)
            fragment = text[start:end].strip()
            if fragment:
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": fragment,
                        "page": page,
                        "section": section,
                    }
                )
                chunk_index += 1
            if end >= len(text):
                break
            start = max(0, end - chunk_overlap_chars)

    return chunks
