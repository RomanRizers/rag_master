from fastapi import FastAPI

from app.api import api_router
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import request_logging_middleware


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Paragraph Search Service")
    app.middleware("http")(request_logging_middleware)
    app.include_router(api_router)
    register_error_handlers(app)
    return app


app = create_app()
