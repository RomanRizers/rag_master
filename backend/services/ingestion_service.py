from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

import structlog

from backend.core.exceptions import ApiError, DocumentError, ParsingError
from backend.ingestion import chunk_blocks, parse_document
from backend.services.api_service import ApiService
from backend.services.document_service import DocumentService

logger = structlog.get_logger("ingestion")


class IngestionService:
    def __init__(self, document_service: DocumentService, api_service: ApiService | None = None):
        self.document_service = document_service
        self.api_service = api_service or ApiService()
        self._jobs: dict[str, dict] = {}
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingestion")

    def start_indexing(self, document_id: str) -> dict:
        self.document_service.get_document(document_id)
        job_id = str(uuid4())
        job = {
            "job_id": job_id,
            "document_id": document_id,
            "status": "queued",
            "progress": 0,
            "error_code": None,
            "error_message": None,
            "started_at": None,
            "finished_at": None,
        }

        with self._lock:
            self._jobs[job_id] = job

        self.document_service.set_status(document_id, "indexing")
        self._executor.submit(self._run_job, job_id)

        return {"job_id": job_id, "status": "queued", "document_id": document_id}

    def get_job(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise DocumentError(
                    message=f"Job not found: {job_id}",
                    code="job_not_found",
                    status_code=404,
                )
            return dict(job)

    def _run_job(self, job_id: str):
        job = self._update_job(job_id, status="running", progress=5, started_at=_now_iso())
        document_id = job["document_id"]
        logger.info("index_job_started", job_id=job_id, document_id=document_id)
        try:
            document = self.document_service.get_document(document_id)

            blocks = parse_document(
                file_name=document.file_name,
                mime_type=document.mime_type,
                content=document.content_bytes,
            )
            self._update_job(job_id, progress=40)

            chunks = chunk_blocks(blocks)
            if not chunks:
                raise ParsingError(message="No chunks produced from document", code="chunking_failed")
            self._update_job(job_id, progress=70)

            documents_payload = [
                {
                    "content": chunk["content"],
                    "dataframe": None,
                    "keywords": [],
                }
                for chunk in chunks
            ]
            self.api_service.index_documents(document.file_name, documents_payload)

            self.document_service.set_status(document_id, "indexed")
            self._update_job(job_id, status="done", progress=100, finished_at=_now_iso())
            logger.info("index_job_finished", job_id=job_id, document_id=document_id, chunks=len(chunks))
        except ApiError as exc:
            self.document_service.set_status(document_id, "failed")
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                error_code=exc.code,
                error_message=exc.message,
                finished_at=_now_iso(),
            )
            logger.warning("index_job_failed", job_id=job_id, document_id=document_id, error_code=exc.code)
        except Exception as exc:
            self.document_service.set_status(document_id, "failed")
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                error_code="internal_error",
                error_message=str(exc),
                finished_at=_now_iso(),
            )
            logger.exception("index_job_failed_unexpected", job_id=job_id, document_id=document_id)

    def _update_job(self, job_id: str, **changes) -> dict:
        with self._lock:
            job = self._jobs[job_id]
            job.update(changes)
            return dict(job)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
