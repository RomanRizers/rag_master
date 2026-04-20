from __future__ import annotations

from typing import Any


def chunk_blocks(
    blocks: list[dict[str, Any]],
    chunk_size_tokens: int = 600,
    chunk_overlap_tokens: int = 120,
    *,
    tokenizer=None,
) -> list[dict[str, Any]]:
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be > 0")
    if chunk_overlap_tokens < 0:
        raise ValueError("chunk_overlap_tokens must be >= 0")
    if chunk_overlap_tokens >= chunk_size_tokens:
        raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens")

    prepared_blocks = _prepare_blocks(blocks, tokenizer)
    grouped_blocks = _group_blocks(prepared_blocks, chunk_size_tokens)

    chunks: list[dict[str, Any]] = []
    chunk_index = 0
    for group in grouped_blocks:
        if group["token_count"] <= chunk_size_tokens:
            chunks.append(_build_chunk(group["blocks"], group["tokens"], tokenizer, chunk_index))
            chunk_index += 1
            continue

        start = 0
        while start < len(group["tokens"]):
            end = min(len(group["tokens"]), start + chunk_size_tokens)
            fragment_tokens = group["tokens"][start:end]
            chunk = _build_chunk(group["blocks"], fragment_tokens, tokenizer, chunk_index)
            chunks.append(chunk)
            chunk_index += 1
            if end >= len(group["tokens"]):
                break
            start = end - chunk_overlap_tokens

    return chunks


def _tokenize_block(text: str, tokenizer) -> list[Any]:
    if tokenizer is None:
        return text.split()
    return tokenizer.encode(text, add_special_tokens=False)


def _decode_fragment(tokens: list[Any], tokenizer) -> str:
    if tokenizer is None:
        return " ".join(str(token) for token in tokens)
    return tokenizer.decode(tokens, skip_special_tokens=True)


def _prepare_blocks(blocks: list[dict[str, Any]], tokenizer) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for block in blocks:
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        tokens = _tokenize_block(text, tokenizer)
        if not tokens:
            continue
        prepared.append(
            {
                **block,
                "text": text,
                "tokens": tokens,
                "token_count": len(tokens),
                "block_type": str(block.get("block_type") or "paragraph"),
                "heading_path": list(block.get("heading_path") or []),
                "is_table_like": bool(block.get("is_table_like") or False),
            }
        )
    return prepared


def _group_blocks(prepared_blocks: list[dict[str, Any]], chunk_size_tokens: int) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    current_blocks: list[dict[str, Any]] = []
    current_tokens: list[Any] = []

    def flush():
        nonlocal current_blocks, current_tokens
        if not current_blocks:
            return
        groups.append({"blocks": current_blocks, "tokens": current_tokens, "token_count": len(current_tokens)})
        current_blocks = []
        current_tokens = []

    _TABLE_ROWS_PER_GROUP = 10
    table_header: dict[str, Any] | None = None
    table_row_buffer: list[dict[str, Any]] = []

    def flush_table_rows() -> None:
        nonlocal table_header, table_row_buffer
        if not table_row_buffer:
            table_header = None
            return
        header = table_header
        rows = table_row_buffer
        for i in range(0, len(rows), _TABLE_ROWS_PER_GROUP):
            group = rows[i : i + _TABLE_ROWS_PER_GROUP]
            blocks_in = ([header] + group) if header else group
            tokens = sum((b["tokens"] for b in blocks_in), [])
            groups.append({"blocks": blocks_in, "tokens": tokens, "token_count": len(tokens)})
        table_header = None
        table_row_buffer = []

    for block in prepared_blocks:
        block_tokens = block["tokens"]
        block_type = block["block_type"]
        if block_type == "table_row":
            flush()
            # First row of a sequence becomes the header for context
            if table_header is None:
                table_header = block
            else:
                table_row_buffer.append(block)
            continue

        # Any non-table block ends a table sequence
        if table_row_buffer or table_header:
            # If only header collected (single row), just emit it
            if not table_row_buffer and table_header:
                table_row_buffer.append(table_header)
                table_header = None
            flush_table_rows()

        if block_type == "heading":
            flush()
            current_blocks = [block]
            current_tokens = list(block_tokens)
            continue

        should_split = False
        if current_blocks:
            current_heading_path = current_blocks[-1].get("heading_path") or []
            block_heading_path = block.get("heading_path") or []
            if block.get("page") != current_blocks[-1].get("page"):
                should_split = True
            if current_heading_path != block_heading_path and current_blocks[-1].get("block_type") != "heading":
                should_split = True
            if len(current_tokens) + len(block_tokens) > chunk_size_tokens and len(current_tokens) >= max(48, chunk_size_tokens // 2):
                should_split = True

        if should_split:
            flush()

        current_blocks.append(block)
        current_tokens.extend(block_tokens)

    flush_table_rows()
    flush()
    return groups


def _build_chunk(blocks: list[dict[str, Any]], fragment_tokens: list[Any], tokenizer, chunk_index: int) -> dict[str, Any]:
    first_block = blocks[0]
    content = _decode_fragment(fragment_tokens, tokenizer).strip()
    block_types = _dedupe([str(block.get("block_type") or "paragraph") for block in blocks])
    heading_path = list(first_block.get("heading_path") or [])
    return {
        "chunk_index": chunk_index,
        "content": content,
        "token_count": len(fragment_tokens),
        "page": first_block.get("page"),
        "section": first_block.get("section"),
        "block_type": block_types[0] if len(block_types) == 1 else "mixed",
        "block_types": block_types,
        "heading_path": heading_path,
        "is_table_like": any(bool(block.get("is_table_like")) for block in blocks),
    }


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value)
    return ordered
