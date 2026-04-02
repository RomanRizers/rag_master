from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api import api_router
from backend.core.error_handlers import register_error_handlers
from backend.core.logging import configure_logging
from backend.core.middleware import request_logging_middleware
from backend.core.services import build_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = build_services()
    try:
        yield
    finally:
        app.state.services.close()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Paragraph Search Service", lifespan=lifespan)
    app.middleware("http")(request_logging_middleware)
    app.include_router(api_router)
    register_error_handlers(app)
    return app


app = create_app()
