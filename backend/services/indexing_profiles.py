from __future__ import annotations

from backend.core.exceptions import ValidationError


INDEX_PROFILE_PRESETS: dict[str, dict[str, int | str]] = {
    "precision": {
        "profile_mode": "precision",
        "chunk_size_tokens": 220,
        "chunk_overlap_tokens": 40,
        "chunk_keyword_limit": 5,
        "document_keyword_limit": 12,
    },
    "balanced": {
        "profile_mode": "balanced",
        "chunk_size_tokens": 320,
        "chunk_overlap_tokens": 64,
        "chunk_keyword_limit": 6,
        "document_keyword_limit": 16,
    },
    "recall": {
        "profile_mode": "recall",
        "chunk_size_tokens": 480,
        "chunk_overlap_tokens": 96,
        "chunk_keyword_limit": 8,
        "document_keyword_limit": 20,
    },
}

DEFAULT_INDEX_PROFILE_MODE = "balanced"


def resolve_index_profile(
    profile_mode: str | None = None,
    *,
    chunk_size_tokens: int | None = None,
    chunk_overlap_tokens: int | None = None,
    chunk_keyword_limit: int | None = None,
    document_keyword_limit: int | None = None,
) -> dict[str, int | str]:
    normalized_mode = str(profile_mode or DEFAULT_INDEX_PROFILE_MODE).strip().lower()
    if normalized_mode not in INDEX_PROFILE_PRESETS:
        raise ValidationError(
            message=f"Unsupported index profile mode: {normalized_mode}",
            code="invalid_index_profile_mode",
            status_code=400,
        )

    resolved = dict(INDEX_PROFILE_PRESETS[normalized_mode])
    if chunk_size_tokens is not None:
        resolved["chunk_size_tokens"] = int(chunk_size_tokens)
    if chunk_overlap_tokens is not None:
        resolved["chunk_overlap_tokens"] = int(chunk_overlap_tokens)
    if chunk_keyword_limit is not None:
        resolved["chunk_keyword_limit"] = int(chunk_keyword_limit)
    if document_keyword_limit is not None:
        resolved["document_keyword_limit"] = int(document_keyword_limit)

    _validate_profile_values(resolved)
    return resolved


def _validate_profile_values(profile: dict[str, int | str]) -> None:
    chunk_size_tokens = int(profile["chunk_size_tokens"])
    chunk_overlap_tokens = int(profile["chunk_overlap_tokens"])
    chunk_keyword_limit = int(profile["chunk_keyword_limit"])
    document_keyword_limit = int(profile["document_keyword_limit"])

    if chunk_size_tokens < 128 or chunk_size_tokens > 480:
        raise ValidationError(
            message="chunk_size_tokens must be between 128 and 480",
            code="invalid_chunk_size_tokens",
            status_code=400,
        )
    if chunk_overlap_tokens < 0 or chunk_overlap_tokens >= chunk_size_tokens:
        raise ValidationError(
            message="chunk_overlap_tokens must be >= 0 and smaller than chunk_size_tokens",
            code="invalid_chunk_overlap_tokens",
            status_code=400,
        )
    if chunk_keyword_limit < 1 or chunk_keyword_limit > 32:
        raise ValidationError(
            message="chunk_keyword_limit must be between 1 and 32",
            code="invalid_chunk_keyword_limit",
            status_code=400,
        )
    if document_keyword_limit < 1 or document_keyword_limit > 32:
        raise ValidationError(
            message="document_keyword_limit must be between 1 and 32",
            code="invalid_document_keyword_limit",
            status_code=400,
        )
