from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.routes import chat_router
from backend.core.error_handlers import register_error_handlers
from backend.core.config import Config
from backend.core.logging import configure_logging
from backend.core.middleware import request_logging_middleware, rate_limit_middleware
from backend.core.rate_limit import InMemoryRateLimiter
from backend.core.services import build_chat_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = build_chat_services()
    try:
        yield
    finally:
        app.state.services.close()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="RAG Chat & Search Service", lifespan=lifespan)
    app.state.rate_limiter = InMemoryRateLimiter(
        enabled=Config.RATE_LIMIT_ENABLED,
        limits_per_minute={
            "chat": Config.RATE_LIMIT_CHAT_RPM,
        },
    )
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(request_logging_middleware)
    app.include_router(chat_router)
    register_error_handlers(app)
    return app


app = create_app()
