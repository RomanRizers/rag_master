import json

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import ensure_admin_api_key, ensure_json_content_type
from backend.api.schemas import (
    ChatMessageRequest,
    ChatSendMessageResponse,
    ChatSessionCreateResponse,
    ChatSessionListResponse,
    ChatSessionMessagesResponse,
    DocumentIndexResponse,
    DocumentIndexStatsResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    IndexingRequest,
    JobStatusResponse,
    JobListResponse,
    OrphanCleanupRequest,
    OrphanCleanupResponse,
    SearchRequest,
)
from backend.core.exceptions import ValidationError
from backend.core.services import AppServices
from backend.services.api_service import ApiService
from backend.services.chat_service import ChatService
from backend.services.document_service import DocumentService
from backend.services.health_service import HealthService
from backend.services.ingestion_service import IngestionService

api_router = APIRouter()
api_service = None
chat_service = None
document_service = None
ingestion_service = None
health_service = None


def _get_app_services(request: Request) -> AppServices | None:
    return getattr(request.app.state, "services", None)


def get_api_service(request: Request | None = None):
    services = _get_app_services(request) if request is not None else None
    if services is not None:
        return services.api_service
    global api_service
    if api_service is None:
        api_service = ApiService()
    return api_service


def get_chat_service(request: Request | None = None):
    services = _get_app_services(request) if request is not None else None
    if services is not None:
        return services.chat_service
    global chat_service
    if chat_service is None:
        chat_service = ChatService()
    return chat_service


def get_document_service(request: Request | None = None):
    services = _get_app_services(request) if request is not None else None
    if services is not None:
        return services.document_service
    global document_service
    if document_service is None:
        document_service = DocumentService()
    return document_service


def get_ingestion_service(request: Request | None = None):
    services = _get_app_services(request) if request is not None else None
    if services is not None:
        return services.ingestion_service
    global ingestion_service
    if ingestion_service is None:
        ingestion_service = IngestionService(
            document_service=get_document_service(request),
            api_service=get_api_service(request),
        )
    return ingestion_service


def get_health_service(request: Request | None = None):
    services = _get_app_services(request) if request is not None else None
    if services is not None:
        return services.health_service
    global health_service
    if health_service is None:
        health_service = HealthService()
    return health_service


@api_router.get("/")
def index():
    """Health endpoint for backend service."""
    return JSONResponse(content={"status": "ok", "service": "fastapi-backend"})


@api_router.get("/health/live")
async def health_live(request: Request):
    payload = await run_in_threadpool(get_health_service(request).live)
    return JSONResponse(content=payload)


@api_router.get("/health/ready")
async def health_ready(request: Request):
    payload, ready = await run_in_threadpool(get_health_service(request).ready)
    status_code = 200 if ready else 503
    return JSONResponse(content=payload, status_code=status_code)


@api_router.post("/api/searching")
@api_router.post("/searching")
async def search(request: Request, payload: SearchRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос поиска."""
    results = await run_in_threadpool(
        get_api_service(request).search_query,
        payload.query,
        payload.top_k,
        payload.keywords,
    )
    return JSONResponse(content=results)


@api_router.post("/api/indexing")
@api_router.post("/indexing")
async def indexing(request: Request, payload: IndexingRequest, _: None = Depends(ensure_json_content_type)):
    """Обрабатывает запрос на индексацию документов."""
    result = await run_in_threadpool(
        get_api_service(request).index_documents,
        payload.document_name,
        [document.model_dump() for document in payload.documents],
    )
    return JSONResponse(content=result)


@api_router.get("/api/documents")
async def list_documents(request: Request):
    items = await run_in_threadpool(get_document_service(request).list_documents)
    response = DocumentListResponse(documents=items)
    return JSONResponse(content=response.model_dump())


@api_router.post("/api/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source_name: str | None = Form(None),
    tags: list[str] | None = Form(None),
):
    content = await file.read()
    if not content:
        raise ValidationError(message="Uploaded file is empty", code="empty_file")

    document = await run_in_threadpool(
        get_document_service(request).create_document,
        file.filename or "document",
        file.content_type or "application/octet-stream",
        content,
        source_name,
        tags,
    )
    response = DocumentUploadResponse.model_validate(document)
    return JSONResponse(content=response.model_dump(), status_code=201)


@api_router.post("/api/documents/{document_id}/index")
async def index_document(request: Request, document_id: str):
    job = await run_in_threadpool(get_ingestion_service(request).start_indexing, document_id)
    response = DocumentIndexResponse.model_validate(job)
    return JSONResponse(content=response.model_dump(), status_code=202)


@api_router.get("/api/documents/{document_id}/index-stats")
async def get_document_index_stats(request: Request, document_id: str):
    stats = await run_in_threadpool(get_ingestion_service(request).get_document_index_stats, document_id)
    response = DocumentIndexStatsResponse.model_validate(stats)
    return JSONResponse(content=response.model_dump())


@api_router.post("/api/admin/index/orphans/cleanup")
async def cleanup_orphan_index_chunks(
    request: Request,
    payload: OrphanCleanupRequest,
    _: None = Depends(ensure_json_content_type),
    __: None = Depends(ensure_admin_api_key),
):
    result = await run_in_threadpool(
        get_ingestion_service(request).cleanup_orphan_chunks,
        payload.dry_run,
    )
    response = OrphanCleanupResponse.model_validate(result)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/jobs/{job_id}")
async def get_job_status(request: Request, job_id: str):
    job = await run_in_threadpool(get_ingestion_service(request).get_job, job_id)
    response = JobStatusResponse.model_validate(job)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/jobs")
async def list_jobs(request: Request, status: str | None = None, document_id: str | None = None):
    jobs = await run_in_threadpool(get_ingestion_service(request).list_jobs, status, document_id)
    response = JobListResponse(jobs=[JobStatusResponse.model_validate(item) for item in jobs])
    return JSONResponse(content=response.model_dump())


@api_router.post("/api/chat/sessions")
async def create_chat_session(request: Request):
    session = await run_in_threadpool(get_chat_service(request).create_session)
    response = ChatSessionCreateResponse.model_validate(session)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/chat/sessions")
async def list_chat_sessions(request: Request):
    sessions = await run_in_threadpool(get_chat_service(request).list_sessions)
    response = ChatSessionListResponse(sessions=sessions)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(request: Request, session_id: str):
    messages = await run_in_threadpool(get_chat_service(request).get_messages, session_id)
    response = ChatSessionMessagesResponse(session_id=session_id, messages=messages)
    return JSONResponse(content=response.model_dump())


@api_router.post("/api/chat/sessions/{session_id}/messages")
async def send_chat_message(request: Request, payload: ChatMessageRequest, session_id: str):
    user_message, assistant_message = await run_in_threadpool(
        get_chat_service(request).send_message,
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


@api_router.post("/api/chat/sessions/{session_id}/messages/stream")
async def stream_chat_message(request: Request, payload: ChatMessageRequest, session_id: str):
    user_message, citations, token_stream = await run_in_threadpool(
        get_chat_service(request).stream_message,
        session_id,
        payload.message,
        payload.top_k,
        payload.keywords,
    )

    def event_stream():
        for chunk in token_stream:
            yield _sse_event("delta", {"text": chunk})
        yield _sse_event("citations", {"items": citations})
        yield _sse_event(
            "done",
            {
                "session_id": session_id,
                "user_message_id": user_message["id"],
            },
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse_event(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
