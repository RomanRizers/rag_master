import secrets

from fastapi import Request

from backend.core.config import Config
from backend.core.exceptions import ValidationError


def ensure_json_content_type(request: Request):
    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    is_json = media_type == "application/json" or media_type.endswith("+json")

    if not is_json:
        raise ValidationError(
            message="Content-Type must be application/json",
            code="invalid_content_type",
            status_code=415,
        )


def ensure_admin_api_key(request: Request):
    provided = request.headers.get("x-admin-api-key", "")
    expected = Config.ADMIN_API_KEY
    if not provided or not secrets.compare_digest(provided, expected):
        raise ValidationError(
            message="Invalid admin API key",
            code="unauthorized",
            status_code=401,
        )
