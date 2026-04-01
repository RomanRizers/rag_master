from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
import structlog

from backend.core.exceptions import ApiError
from backend.core.responses import error_response_payload

logger = structlog.get_logger("errors")


def register_error_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, error: RequestValidationError):
        errors = error.errors()
        first_error = errors[0] if errors else {}
        location = first_error.get("loc", ())
        field_name = location[-1] if location else None
        error_type = first_error.get("type", "")

        status_code = 400
        code = "invalid_field"
        message = "Validation failed"

        if error_type == "json_invalid":
            code = "invalid_json"
            message = "Request body must contain valid JSON"
        elif field_name == "query" and error_type == "missing":
            message = "Query is required"
        elif field_name == "document_name" and error_type == "missing":
            message = "No document name provided"
        elif field_name == "documents" and error_type == "missing":
            message = "No documents to index"
        elif first_error.get("msg"):
            message = first_error["msg"].replace("Value error, ", "")

        logger.warning(
            "request_validation_error",
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path,
            method=request.method,
            status_code=status_code,
            validation_code=code,
            validation_error_type=error_type,
            field=field_name,
        )
        return JSONResponse(
            content=error_response_payload(
                code=code,
                message=message,
                details={"errors": jsonable_encoder(errors)},
            ),
            status_code=status_code,
        )

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError):
        logger.warning(
            "api_error",
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path,
            method=request.method,
            error_code=error.code,
            status_code=error.status_code,
        )
        return JSONResponse(
            content=error_response_payload(
                code=error.code,
                message=error.message,
                details=error.details,
            ),
            status_code=error.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception):
        logger.exception(
            "unexpected_error",
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path,
            method=request.method,
            error_type=error.__class__.__name__,
        )
        return JSONResponse(
            content=error_response_payload(
                code="internal_error",
                message="Internal server error",
                details={"type": error.__class__.__name__},
            ),
            status_code=500,
        )
