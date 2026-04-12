from __future__ import annotations

import re


_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")

_ALIASES = {
    "зра": ["запорно регулирующая арматура", "запорная арматура", "регулирующая арматура"],
    "сдт": ["соединительные детали трубопроводов", "детали трубопроводов"],
    "нк": ["неразрушающий контроль", "неразрушающий контроль сварных швов"],
    "гост": ["государственный стандарт"],
}


def normalize_query(query: str) -> dict:
    clean_query = " ".join(str(query or "").strip().split())
    lowered = clean_query.lower()
    tokens = _TOKEN_RE.findall(lowered)

    expansions: list[str] = []
    for token in tokens:
        expansions.extend(_ALIASES.get(token, []))

    expanded_terms = _dedupe([*tokens, *expansions])
    expanded_query = clean_query
    if expansions:
        expanded_query = f"{clean_query}\n\nСинонимы и расширения запроса: {'; '.join(_dedupe(expansions))}"

    exact_identifiers = [
        token
        for token in tokens
        if any(char.isdigit() for char in token) or "-" in token or "/" in token
    ]

    return {
        "raw_query": clean_query,
        "normalized_query": lowered,
        "query_tokens": tokens,
        "expanded_terms": expanded_terms,
        "expanded_query": expanded_query,
        "exact_identifiers": _dedupe(exact_identifiers),
    }


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for item in items:
        normalized = str(item).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(str(item).strip())
    return ordered
