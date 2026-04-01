from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import Config
from app.services.api_service import ApiService
from app.validation import parse_json_body, validate_indexing_request, validate_search_request

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
async def search(request: Request):
    """Обрабатывает запрос поиска."""
    data = await parse_json_body(request)
    query, top_k, keywords = validate_search_request(
        data,
        top_k_default=Config.TOP_K_DEFAULT,
        top_k_max=Config.TOP_K_MAX,
    )

    results = get_api_service().search_query(query, top_k, keywords)
    return JSONResponse(content=results)


@api_router.post("/indexing")
async def indexing(request: Request):
    """Обрабатывает запрос на индексацию документов."""
    data = await parse_json_body(request)
    document_name, documents = validate_indexing_request(data)

    result = get_api_service().index_documents(document_name, documents)
    return JSONResponse(content=result)
