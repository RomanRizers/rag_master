from __future__ import annotations

from datetime import datetime, timezone
import time
from uuid import uuid4

import structlog

from backend.core.config import Config
from backend.core.exceptions import ApiError, DocumentError, ParsingError
from backend.infrastructure.job_store import JobStore, create_job_store
from backend.ingestion import chunk_blocks, parse_document
from backend.services.api_service import ApiService
from backend.services.document_service import DocumentService

logger = structlog.get_logger("ingestion")


class IngestionService:
    MAX_RETRIES = 3

    def __init__(
        self,
        document_service: DocumentService,
        api_service: ApiService | None = None,
        job_store: JobStore | None = None,
    ):
        self.document_service = document_service
        self.api_service = api_service or ApiService()
        self.job_store = job_store or create_job_store()

    def start_indexing(self, document_id: str) -> dict:
        self.document_service.get_document(document_id)
        active_job = self._find_active_job_for_document(document_id)
        if active_job is not None:
            return {
                "job_id": active_job["job_id"],
                "status": active_job["status"],
                "document_id": document_id,
            }

        job_id = str(uuid4())
        job = {
            "job_id": job_id,
            "document_id": document_id,
            "status": "queued",
            "progress": 0,
            "attempt": 0,
            "error_code": None,
            "error_message": None,
            "started_at": None,
            "finished_at": None,
        }

        self.job_store.create_job(job)
        return {"job_id": job_id, "status": "queued", "document_id": document_id}

    def claim_next_job(self) -> dict | None:
        return self.job_store.claim_next_queued(started_at=_now_iso())

    def process_job(self, job_id: str):
        job = self.get_job(job_id)
        if job["status"] == "queued":
            claimed = self.job_store.claim_next_queued(started_at=_now_iso())
            if claimed is None:
                return
            if claimed["job_id"] != job_id:
                return
            job = claimed
        if job["status"] != "running":
            return
        self._run_job(job_id)

    def get_job(self, job_id: str) -> dict:
        job = self.job_store.get_job(job_id)
        if job is None:
            raise DocumentError(
                message=f"Job not found: {job_id}",
                code="job_not_found",
                status_code=404,
            )
        return job

    def list_jobs(self, status: str | None = None, document_id: str | None = None) -> list[dict]:
        jobs = self.job_store.list_jobs()
        if status:
            jobs = [item for item in jobs if item.get("status") == status]
        if document_id:
            jobs = [item for item in jobs if item.get("document_id") == document_id]
        jobs.sort(key=lambda item: item.get("started_at") or "", reverse=True)
        return jobs

    def _run_job(self, job_id: str):
        job = self.get_job(job_id)
        if job["status"] != "running":
            return

        job = self._update_job(job_id, progress=max(5, int(job.get("progress") or 0)), started_at=job.get("started_at") or _now_iso())
        document_id = job["document_id"]
        self.document_service.set_status(document_id, "indexing")
        logger.info("index_job_started", job_id=job_id, document_id=document_id)
        for attempt in range(1, self.MAX_RETRIES + 1):
            self._update_job(job_id, attempt=attempt, error_code=None, error_message=None)
            try:
                self._run_job_once(job_id=job_id, document_id=document_id)
                self.document_service.set_status(document_id, "indexed")
                self._update_job(job_id, status="done", progress=100, finished_at=_now_iso())
                return
            except ApiError as exc:
                should_retry = self._is_retryable_error(exc) and attempt < self.MAX_RETRIES
                logger.warning(
                    "index_job_failed",
                    job_id=job_id,
                    document_id=document_id,
                    error_code=exc.code,
                    attempt=attempt,
                    retry=should_retry,
                )
                if should_retry:
                    self._update_job(
                        job_id,
                        status="running",
                        progress=10,
                        error_code=exc.code,
                        error_message=f"{exc.message}; retrying",
                    )
                    backoff_seconds = max(0.0, Config.INGESTION_RETRY_BACKOFF_SECONDS) * attempt
                    if backoff_seconds > 0:
                        time.sleep(backoff_seconds)
                    continue

                self.document_service.set_status(document_id, "failed")
                self._update_job(
                    job_id,
                    status="failed",
                    progress=100,
                    error_code=exc.code,
                    error_message=exc.message,
                    finished_at=_now_iso(),
                )
                return
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
                return

    def _run_job_once(self, job_id: str, document_id: str):
        document = self.document_service.get_document(document_id)
        document_bytes = self.document_service.read_content(document_id)
        self.api_service.delete_document_chunks(document_id)

        blocks = parse_document(
            file_name=document.file_name,
            mime_type=document.mime_type,
            content=document_bytes,
        )
        self._update_job(job_id, progress=40)

        chunks = chunk_blocks(
            blocks,
            chunk_size_tokens=Config.CHUNK_SIZE_TOKENS,
            chunk_overlap_tokens=Config.CHUNK_OVERLAP_TOKENS,
        )
        if not chunks:
            raise ParsingError(message="No chunks produced from document", code="chunking_failed")
        self._update_job(job_id, progress=70)

        documents_payload = [
            {
                "content": chunk["content"],
                "dataframe": None,
                "keywords": [],
                "metadata": {
                    "document_id": document_id,
                    "chunk_index": chunk.get("chunk_index"),
                    "token_count": chunk.get("token_count"),
                    "page": chunk.get("page"),
                    "section": chunk.get("section"),
                },
            }
            for chunk in chunks
        ]
        self.api_service.index_documents(document.file_name, documents_payload)
        logger.info("index_job_finished", job_id=job_id, document_id=document_id, chunks=len(chunks))

    def _update_job(self, job_id: str, **changes) -> dict:
        return self.job_store.update_job(job_id, **changes)

    @staticmethod
    def _is_retryable_error(error: ApiError) -> bool:
        return error.code in {"storage_error", "vectorization_error"}

    def _find_active_job_for_document(self, document_id: str) -> dict | None:
        for job in self.job_store.list_jobs():
            if job.get("document_id") == document_id and job.get("status") in {"queued", "running"}:
                return job
        return None

    def close(self):
        close_fn = getattr(self.job_store, "close", None)
        if callable(close_fn):
            close_fn()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
