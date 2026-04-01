from fastapi import Request

from backend.core.exceptions import ValidationError


def ensure_json_content_type(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise ValidationError(
            message="Content-Type must be application/json",
            code="invalid_content_type",
            status_code=415,
        )
