from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import ensure_json_content_type
from backend.api.schemas import (
    ChatMessageRequest,
    ChatSendMessageResponse,
    ChatSessionCreateResponse,
    ChatSessionMessagesResponse,
    IndexingRequest,
    SearchRequest,
)
from backend.services.api_service import ApiService
from backend.services.chat_service import ChatService

api_router = APIRouter()
api_service = None
chat_service = None


def get_api_service():
    global api_service
    if api_service is None:
        api_service = ApiService()
    return api_service


def get_chat_service():
    global chat_service
    if chat_service is None:
        chat_service = ChatService()
    return chat_service


@api_router.get("/")
def index():
    """Health endpoint for backend service."""
    return JSONResponse(content={"status": "ok", "service": "fastapi-backend"})


@api_router.post("/api/searching")
@api_router.post("/searching")
async def search(payload: SearchRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос поиска."""
    results = await run_in_threadpool(
        get_api_service().search_query,
        payload.query,
        payload.top_k,
        payload.keywords,
    )
    return JSONResponse(content=results)


@api_router.post("/api/indexing")
@api_router.post("/indexing")
async def indexing(payload: IndexingRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос на индексацию документов."""
    result = await run_in_threadpool(
        get_api_service().index_documents,
        payload.document_name,
        [document.model_dump() for document in payload.documents],
    )
    return JSONResponse(content=result)


@api_router.post("/api/chat/sessions")
async def create_chat_session():
    session = await run_in_threadpool(get_chat_service().create_session)
    response = ChatSessionCreateResponse.model_validate(session)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str):
    messages = await run_in_threadpool(get_chat_service().get_messages, session_id)
    response = ChatSessionMessagesResponse(session_id=session_id, messages=messages)
    return JSONResponse(content=response.model_dump())


@api_router.post("/api/chat/sessions/{session_id}/messages")
async def send_chat_message(payload: ChatMessageRequest, session_id: str):
    user_message, assistant_message = await run_in_threadpool(
        get_chat_service().send_message,
        session_id,
        payload.message,
        payload.top_k,
        payload.keywords,
    )
    response = ChatSendMessageResponse(
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_message,
    )
    return JSONResponse(content=response.model_dump())
