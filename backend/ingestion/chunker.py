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

    chunks: list[dict[str, Any]] = []
    chunk_index = 0

    for block in blocks:
        text = str(block.get("text") or "").strip()
        if not text:
            continue

        tokens = _tokenize_block(text, tokenizer)
        if not tokens:
            continue

        page = block.get("page")
        section = block.get("section")

        start = 0
        while start < len(tokens):
            end = min(len(tokens), start + chunk_size_tokens)
            fragment_tokens = tokens[start:end]
            fragment = _decode_fragment(fragment_tokens, tokenizer).strip()

            if fragment:
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": fragment,
                        "token_count": len(fragment_tokens),
                        "page": page,
                        "section": section,
                    }
                )
                chunk_index += 1

            if end >= len(tokens):
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
