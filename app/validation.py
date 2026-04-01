import json

from app.exceptions import ValidationError


async def parse_json_body(request):
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise ValidationError(
            message="Content-Type must be application/json",
            code="invalid_content_type",
            status_code=415,
        )

    try:
        data = await request.json()
    except json.JSONDecodeError as error:
        raise ValidationError(
            message="Request body must contain valid JSON",
            code="invalid_json",
            details={"reason": str(error)},
        ) from error

    if not isinstance(data, dict):
        raise ValidationError(
            message="JSON body must be an object",
            code="invalid_json_shape",
        )
    return data


def _require_non_empty_string(payload, key, message=None):
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(message=message or f"'{key}' must be a non-empty string", code="invalid_field")
    return value.strip()


def _parse_keywords(payload, key):
    keywords = payload.get(key)
    if keywords is None:
        return None
    if not isinstance(keywords, list) or any(not isinstance(item, str) or not item.strip() for item in keywords):
        raise ValidationError(message=f"'{key}' must be a list of non-empty strings", code="invalid_field")
    return [keyword.strip() for keyword in keywords]


def parse_top_k(payload, key, default, max_value):
    value = payload.get(key, default)
    if isinstance(value, bool):
        raise ValidationError(message=f"'{key}' must be an integer", code="invalid_field")
    if not isinstance(value, int):
        raise ValidationError(message=f"'{key}' must be an integer", code="invalid_field")
    if value < 1 or value > max_value:
        raise ValidationError(
            message=f"'{key}' must be between 1 and {max_value}",
            code="invalid_field",
            details={"min": 1, "max": max_value},
        )
    return value


def validate_search_request(payload, top_k_default, top_k_max):
    query = _require_non_empty_string(payload, "query", message="Query is required")
    top_k = parse_top_k(payload, "top_k", default=top_k_default, max_value=top_k_max)
    keywords = _parse_keywords(payload, "keywords")
    return query, top_k, keywords


def validate_indexing_request(payload):
    document_name = _require_non_empty_string(payload, "document_name", message="No document name provided")
    documents = payload.get("documents")

    if not isinstance(documents, list) or len(documents) == 0:
        raise ValidationError(message="No documents to index", code="invalid_field")

    normalized_documents = []
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValidationError(
                message="Each document must be an object",
                code="invalid_field",
                details={"index": index},
            )

        content = document.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValidationError(
                message="Each document must include non-empty 'content'",
                code="invalid_field",
                details={"index": index},
            )

        keywords = document.get("keywords", [])
        if keywords is None:
            keywords = []
        if not isinstance(keywords, list) or any(not isinstance(item, str) or not item.strip() for item in keywords):
            raise ValidationError(
                message="'keywords' must be a list of non-empty strings",
                code="invalid_field",
                details={"index": index},
            )

        dataframe = document.get("dataframe")
        if dataframe is not None and not isinstance(dataframe, str):
            raise ValidationError(
                message="'dataframe' must be a string when provided",
                code="invalid_field",
                details={"index": index},
            )

        normalized_documents.append(
            {
                "content": content.strip(),
                "keywords": [keyword.strip() for keyword in keywords],
                "dataframe": dataframe,
            }
        )

    return document_name, normalized_documents
