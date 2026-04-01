from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.schemas import IndexingRequest, SearchRequest
from app.services.api_service import ApiService
from app.validation import ensure_json_content_type

api_router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
api_service = None


def get_api_service():
    global api_service
    if api_service is None:
        api_service = ApiService()
    return api_service


@api_router.get("/")
def index(request: Request):
    """Возвращает HTML-файл фронтенда."""
    return templates.TemplateResponse("index.html", {"request": request})


@api_router.post("/searching")
async def search(payload: SearchRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос поиска."""
    results = get_api_service().search_query(payload.query, payload.top_k, payload.keywords)
    return JSONResponse(content=results)


@api_router.post("/indexing")
async def indexing(payload: IndexingRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос на индексацию документов."""
    result = get_api_service().index_documents(
        payload.document_name,
        [document.model_dump() for document in payload.documents],
    )
    return JSONResponse(content=result)
