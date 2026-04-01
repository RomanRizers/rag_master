from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import ApiError
from app.responses import error_response_payload


def register_error_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError):
        return JSONResponse(
            content=error_response_payload(
                code=error.code,
                message=error.message,
                details=error.details,
            ),
            status_code=error.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception):
        return JSONResponse(
            content=error_response_payload(
                code="internal_error",
                message="Internal server error",
                details={"type": error.__class__.__name__},
            ),
            status_code=500,
        )
