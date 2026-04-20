import json
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import ensure_admin_api_key, ensure_json_content_type
from backend.api.schemas import (
    ChatMessageRequest,
    ChatSendMessageResponse,
    ChatSessionCreateResponse,
    ChatSessionListResponse,
    ChatSessionMessagesResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseCreateResponse,
    KnowledgeBaseRenameRequest,
    KnowledgeBaseReindexResponse,
    KnowledgeBaseResponse,
    DocumentIndexResponse,
    DocumentChunksResponse,
    DocumentIndexStatsResponse,
    IndexDocumentRequest,
    KnowledgeBaseListResponse,
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

api_router = APIRouter()
chat_router = APIRouter()


# ---------------------------------------------------------------------------
# Service getters — look in app.state.services (ApiServices or ChatServices)
# ---------------------------------------------------------------------------

def _get_services(request: Request):
    return getattr(request.app.state, "services", None)


def get_api_service(request: Request):
    services = _get_services(request)
    if services is not None:
        return services.api_service
    from backend.services.api_service import ApiService
    return ApiService()


def get_chat_service(request: Request):
    services = _get_services(request)
    if services is not None:
        return services.chat_service
    from backend.services.chat_service import ChatService
    return ChatService()


def get_document_service(request: Request):
    services = _get_services(request)
    if services is not None:
        return services.document_service
    from backend.services.document_service import DocumentService
    return DocumentService()


def get_ingestion_service(request: Request):
    services = _get_services(request)
    if services is not None:
        return services.ingestion_service
    from backend.services.ingestion_service import IngestionService
    return IngestionService(
        document_service=get_document_service(request),
        api_service=get_api_service(request),
    )


def get_health_service(request: Request):
    services = _get_services(request)
    if services is not None:
        return services.health_service
    from backend.services.health_service import HealthService
    return HealthService()


# ---------------------------------------------------------------------------
# api_router — CRUD: documents, knowledge-bases, jobs, admin, health
# ---------------------------------------------------------------------------

@api_router.get("/")
def index():
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


@api_router.get("/api/documents")
async def list_documents(request: Request):
    items = await run_in_threadpool(get_document_service(request).list_documents)
    response = DocumentListResponse(documents=items)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/knowledge-bases")
async def list_knowledge_bases(request: Request):
    items = await run_in_threadpool(get_document_service(request).list_knowledge_bases)
    response = KnowledgeBaseListResponse(knowledge_bases=items)
    return JSONResponse(content=response.model_dump())


@api_router.post("/api/knowledge-bases")
async def create_knowledge_base(request: Request, payload: KnowledgeBaseCreateRequest, _: None = Depends(ensure_json_content_type)):
    item = await run_in_threadpool(get_document_service(request).create_knowledge_base, payload.name)
    response = KnowledgeBaseCreateResponse.model_validate(item)
    return JSONResponse(content=response.model_dump(), status_code=201)


@api_router.patch("/api/knowledge-bases/{knowledge_base_name}")
async def rename_knowledge_base(
    request: Request,
    knowledge_base_name: str,
    payload: KnowledgeBaseRenameRequest,
    _: None = Depends(ensure_json_content_type),
):
    service = get_document_service(request)
    target_name = knowledge_base_name
    if payload.name and payload.name != knowledge_base_name:
        renamed = await run_in_threadpool(
            service.rename_knowledge_base,
            knowledge_base_name,
            payload.name,
        )
        target_name = renamed["name"]

    item = await run_in_threadpool(
        lambda: service.update_knowledge_base(
            target_name,
            profile_mode=payload.profile_mode,
            chunk_size_tokens=payload.chunk_size_tokens,
            chunk_overlap_tokens=payload.chunk_overlap_tokens,
            chunk_keyword_limit=payload.chunk_keyword_limit,
            document_keyword_limit=payload.document_keyword_limit,
        )
    )
    response = KnowledgeBaseResponse.model_validate(item)
    return JSONResponse(content=response.model_dump())


@api_router.post("/api/knowledge-bases/{knowledge_base_name}/reindex")
async def reindex_knowledge_base(request: Request, knowledge_base_name: str):
    result = await run_in_threadpool(
        get_ingestion_service(request).start_indexing_knowledge_base,
        knowledge_base_name,
    )
    response = KnowledgeBaseReindexResponse.model_validate(result)
    return JSONResponse(content=response.model_dump(), status_code=202)


@api_router.delete("/api/knowledge-bases/{knowledge_base_name}")
async def delete_knowledge_base(request: Request, knowledge_base_name: str):
    item = await run_in_threadpool(get_document_service(request).delete_knowledge_base, knowledge_base_name)
    response = KnowledgeBaseResponse.model_validate(item)
    return JSONResponse(content={"status": "deleted", "knowledge_base": response.model_dump()})


@api_router.delete("/api/documents/{document_id}")
async def delete_document(request: Request, document_id: str):
    deleted = await run_in_threadpool(get_ingestion_service(request).delete_document, document_id)
    return JSONResponse(content={"status": "deleted", "document": deleted})


@api_router.post("/api/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source_name: str | None = Form(None),
    tags: list[str] | None = Form(None),
    knowledge_base: str | None = Form(None),
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
        knowledge_base,
    )
    response = DocumentUploadResponse.model_validate(document)
    return JSONResponse(content=response.model_dump(), status_code=201)


@api_router.post("/api/documents/{document_id}/index")
async def index_document(
    request: Request,
    document_id: str,
    body: IndexDocumentRequest | None = Body(default=None),
):
    delimiters = body.delimiters if body else None
    job = await run_in_threadpool(
        get_ingestion_service(request).start_indexing,
        document_id,
        delimiters=delimiters,
    )
    response = DocumentIndexResponse.model_validate(job)
    return JSONResponse(content=response.model_dump(), status_code=202)


@api_router.get("/api/documents/{document_id}/index-stats")
async def get_document_index_stats(request: Request, document_id: str):
    stats = await run_in_threadpool(get_ingestion_service(request).get_document_index_stats, document_id)
    response = DocumentIndexStatsResponse.model_validate(stats)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/documents/{document_id}/chunks")
async def get_document_chunks(request: Request, document_id: str):
    payload = await run_in_threadpool(get_ingestion_service(request).get_document_chunks, document_id)
    response = DocumentChunksResponse.model_validate(payload)
    return JSONResponse(content=response.model_dump())


@api_router.get("/api/documents/{document_id}/file")
async def download_document_file(request: Request, document_id: str):
    doc_service = get_document_service(request)
    record = await run_in_threadpool(doc_service.get_document, document_id)
    content = await run_in_threadpool(doc_service.read_content, document_id)
    # RFC 5987: use filename*=UTF-8''<percent-encoded> for non-ASCII filenames
    encoded_name = quote(record.file_name or "file", safe="")
    content_disposition = f"inline; filename*=UTF-8''{encoded_name}"
    # Use Response (not StreamingResponse) so Content-Length is set — required
    # by pdfjs to seek within large PDFs and enable byte-range requests.
    return Response(
        content=content,
        media_type=record.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": content_disposition,
            "Accept-Ranges": "bytes",
        },
    )


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


# ---------------------------------------------------------------------------
# chat_router — AI runtime: search, indexing API, chat sessions
# ---------------------------------------------------------------------------

@chat_router.post("/api/searching")
@chat_router.post("/searching")
async def search(request: Request, payload: SearchRequest, _: None = Depends(ensure_json_content_type)):
    results = await run_in_threadpool(
        get_api_service(request).search_query,
        payload.query,
        payload.top_k,
        payload.keywords,
        payload.filters.model_dump(exclude_none=True) if payload.filters else None,
    )
    return JSONResponse(content=results)


@chat_router.post("/api/indexing")
@chat_router.post("/indexing")
async def indexing(request: Request, payload: IndexingRequest, _: None = Depends(ensure_json_content_type)):
    result = await run_in_threadpool(
        get_api_service(request).index_documents,
        payload.document_name,
        [document.model_dump() for document in payload.documents],
    )
    return JSONResponse(content=result)


@chat_router.post("/api/chat/sessions")
async def create_chat_session(request: Request):
    session = await run_in_threadpool(get_chat_service(request).create_session)
    response = ChatSessionCreateResponse.model_validate(session)
    return JSONResponse(content=response.model_dump())


@chat_router.get("/api/chat/sessions")
async def list_chat_sessions(request: Request):
    sessions = await run_in_threadpool(get_chat_service(request).list_sessions)
    response = ChatSessionListResponse(sessions=sessions)
    return JSONResponse(content=response.model_dump())


@chat_router.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(request: Request, session_id: str):
    deleted = await run_in_threadpool(get_chat_service(request).delete_session, session_id)
    return JSONResponse(content={"status": "deleted", "session": deleted})


@chat_router.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(request: Request, session_id: str):
    messages = await run_in_threadpool(get_chat_service(request).get_messages, session_id)
    response = ChatSessionMessagesResponse(session_id=session_id, messages=messages)
    return JSONResponse(content=response.model_dump())


@chat_router.post("/api/chat/sessions/{session_id}/messages")
async def send_chat_message(request: Request, payload: ChatMessageRequest, session_id: str):
    user_message, assistant_message = await run_in_threadpool(
        get_chat_service(request).send_message,
        session_id,
        payload.message,
        payload.top_k,
        payload.keywords,
        payload.filters.model_dump(exclude_none=True) if payload.filters else None,
    )
    response = ChatSendMessageResponse(
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_message,
    )
    return JSONResponse(content=response.model_dump())


@chat_router.post("/api/chat/sessions/{session_id}/messages/stream")
async def stream_chat_message(request: Request, payload: ChatMessageRequest, session_id: str):
    user_message, citations, token_stream = await run_in_threadpool(
        get_chat_service(request).stream_message,
        session_id,
        payload.message,
        payload.top_k,
        payload.keywords,
        payload.filters.model_dump(exclude_none=True) if payload.filters else None,
    )

    def event_stream():
        try:
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
        except Exception as exc:
            yield _sse_event("error", {"code": "stream_error", "message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse_event(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
