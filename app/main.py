from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.error_handlers import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Paragraph Search Service")
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(api_router)
    register_error_handlers(app)
    return app


app = create_app()
