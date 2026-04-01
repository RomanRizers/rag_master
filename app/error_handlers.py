from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

from app.exceptions import ApiError
from app.responses import error_response_payload

logger = structlog.get_logger("errors")


def register_error_handlers(app: FastAPI):
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
