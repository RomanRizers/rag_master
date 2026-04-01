from fastapi import FastAPI

from backend.api import api_router
from backend.core.error_handlers import register_error_handlers
from backend.core.logging import configure_logging
from backend.core.middleware import request_logging_middleware


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Paragraph Search Service")
    app.middleware("http")(request_logging_middleware)
    app.include_router(api_router)
    register_error_handlers(app)
    return app


app = create_app()
