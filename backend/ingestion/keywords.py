from __future__ import annotations

import math
import re
from collections import Counter, defaultdict


_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9][a-zA-Zа-яА-ЯёЁ0-9\\-]{1,}")

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "with",
    "в", "во", "все", "вы", "для", "до", "его", "ее", "же", "за", "и", "из", "или", "их",
    "к", "как", "ко", "на", "над", "не", "но", "о", "об", "от", "по", "под", "при", "с", "со",
    "так", "то", "у", "что", "это",
}

_BOILERPLATE_TOKENS = {
    "рис", "рисунок", "табл", "таблица", "table", "figure", "стр", "page", "пункт", "раздел",
}


def extract_document_keywords(
    blocks: list[dict],
    *,
    document_limit: int,
) -> list[str]:
    source_text = "\n".join(_prepare_block_text(block) for block in blocks if _prepare_block_text(block))
    if not source_text.strip():
        return []
    return _extract_keywords(source_text, limit=document_limit)


def extract_chunk_keywords(
    content: str,
    *,
    limit: int,
    document_keywords: list[str] | None = None,
) -> list[str]:
    local_keywords = _extract_keywords(content, limit=max(limit * 2, limit))
    local_set = {item.lower(): item for item in local_keywords}
    inherited: list[str] = []
    normalized_content = f" {content.lower()} "
    for keyword in document_keywords or []:
        if len(inherited) >= limit:
            break
        lowered = keyword.lower()
        if lowered in local_set:
            continue
        if lowered in normalized_content:
            inherited.append(keyword)
    ordered = list(local_keywords)
    ordered.extend(inherited)
    return _dedupe_preserve_order(ordered)[:limit]


def _extract_keywords(text: str, *, limit: int) -> list[str]:
    tokens = _tokenize(text)
    if not tokens or limit <= 0:
        return []

    candidates = _build_candidates(tokens)
    scored: list[tuple[float, str]] = []
    for phrase, positions in candidates.items():
        normalized = phrase.lower()
        if _is_bad_candidate(normalized):
            continue
        score = len(positions)
        score += 1.5 if positions[0] < 24 else 0.0
        score += 0.8 if len(normalized.split()) > 1 else 0.0
        score += min(1.2, math.log(len(normalized) + 1, 8))
        scored.append((score, phrase))

    ranked = sorted(scored, key=lambda item: (-item[0], len(item[1]), item[1]))
    return _dedupe_preserve_order(phrase for _, phrase in ranked)[:limit]


def _prepare_block_text(block: dict) -> str:
    section = str(block.get("section") or "").strip()
    text = str(block.get("text") or "").strip()
    if section and text and not text.lower().startswith(section.lower()):
        return f"{section}. {text}"
    return text or section


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]


def _build_candidates(tokens: list[str]) -> dict[str, list[int]]:
    candidates: dict[str, list[int]] = defaultdict(list)
    for index, token in enumerate(tokens):
        if _is_noise_token(token):
            continue
        candidates[token].append(index)
        for size in (2, 3):
            end = index + size
            if end > len(tokens):
                break
            phrase_tokens = tokens[index:end]
            if any(_is_noise_token(item) for item in phrase_tokens):
                continue
            phrase = " ".join(phrase_tokens)
            candidates[phrase].append(index)
    return candidates


def _is_bad_candidate(candidate: str) -> bool:
    if candidate in _STOPWORDS:
        return True
    parts = candidate.split()
    if all(part in _STOPWORDS for part in parts):
        return True
    if any(part in _BOILERPLATE_TOKENS for part in parts):
        return True
    if re.fullmatch(r"[0-9\\-\\.]+", candidate):
        return True
    if len(candidate) < 3:
        return True
    return False


def _is_noise_token(token: str) -> bool:
    if token in _STOPWORDS or token in _BOILERPLATE_TOKENS:
        return True
    if len(token) < 2:
        return True
    if re.fullmatch(r"[0-9\\-\\.]+", token):
        return True
    return False


def _dedupe_preserve_order(items) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        normalized = str(item).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(str(item).strip())
    return result
