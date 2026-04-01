from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import ensure_json_content_type
from app.api.schemas import IndexingRequest, SearchRequest
from app.services.api_service import ApiService

api_router = APIRouter()
api_service = None


def get_api_service():
    global api_service
    if api_service is None:
        api_service = ApiService()
    return api_service


@api_router.get("/")
def index():
    """Health endpoint for backend service."""
    return JSONResponse(content={"status": "ok", "service": "fastapi-backend"})


@api_router.post("/api/searching")
@api_router.post("/searching")
async def search(payload: SearchRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос поиска."""
    results = get_api_service().search_query(payload.query, payload.top_k, payload.keywords)
    return JSONResponse(content=results)


@api_router.post("/api/indexing")
@api_router.post("/indexing")
async def indexing(payload: IndexingRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос на индексацию документов."""
    result = get_api_service().index_documents(
        payload.document_name,
        [document.model_dump() for document in payload.documents],
    )
    return JSONResponse(content=result)
