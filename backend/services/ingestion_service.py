from __future__ import annotations

from datetime import datetime, timezone
import time
from uuid import uuid4

import structlog

from backend.core.config import Config
from backend.core.exceptions import ApiError, DocumentError, ParsingError
from backend.infrastructure.job_store import JobStore, create_job_store
from backend.ingestion import chunk_blocks, parse_document
from backend.ingestion.keywords import extract_chunk_keywords, extract_document_keywords
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

    def start_indexing_knowledge_base(self, knowledge_base_name: str) -> dict:
        knowledge_base = self.document_service.get_knowledge_base(knowledge_base_name)
        queued_jobs = 0
        for document in self.document_service.list_documents():
            if document.get("knowledge_base") != knowledge_base["name"]:
                continue
            job = self.start_indexing(document["document_id"])
            if job.get("status") == "queued":
                queued_jobs += 1
        return {"knowledge_base": knowledge_base["name"], "queued_jobs": queued_jobs}

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

    def delete_document(self, document_id: str) -> dict:
        self.document_service.get_document(document_id)
        self.api_service.delete_document_chunks(document_id)
        self.job_store.delete_jobs_for_document(document_id)
        return self.document_service.delete_document(document_id)

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
        knowledge_base = self.document_service.get_knowledge_base(document.knowledge_base)
        document_bytes = self.document_service.read_content(document_id)
        self.api_service.delete_document_chunks(document_id)

        blocks = parse_document(
            file_name=document.file_name,
            mime_type=document.mime_type,
            content=document_bytes,
        )
        self._update_job(job_id, progress=40)

        tokenizer = getattr(getattr(self.api_service, "vectorizer", None), "tokenizer", None)
        chunks = chunk_blocks(
            blocks,
            chunk_size_tokens=int(knowledge_base["chunk_size_tokens"]),
            chunk_overlap_tokens=int(knowledge_base["chunk_overlap_tokens"]),
            tokenizer=tokenizer,
        )
        if not chunks:
            raise ParsingError(message="No chunks produced from document", code="chunking_failed")
        self._update_job(job_id, progress=70)

        document_keywords = extract_document_keywords(
            blocks,
            document_limit=int(knowledge_base["document_keyword_limit"]),
        )

        documents_payload = [
            {
                "content": chunk["content"],
                "dataframe": None,
                "keywords": extract_chunk_keywords(
                    chunk["content"],
                    limit=int(knowledge_base["chunk_keyword_limit"]),
                    document_keywords=document_keywords,
                ),
                "metadata": {
                    "document_id": document_id,
                    "chunk_id": f"{document_id}:{chunk.get('chunk_index')}",
                    "chunk_index": chunk.get("chunk_index"),
                    "token_count": chunk.get("token_count"),
                    "page": chunk.get("page"),
                    "section": chunk.get("section"),
                    "block_type": chunk.get("block_type"),
                    "block_types": list(chunk.get("block_types") or []),
                    "heading_path": list(chunk.get("heading_path") or []),
                    "is_table_like": bool(chunk.get("is_table_like") or False),
                    "source_uri": document.object_key,
                    "source_name": document.source_name,
                    "tags": list(document.tags),
                    "knowledge_base": document.knowledge_base,
                    "document_keywords": list(document_keywords),
                    "index_profile": {
                        "profile_mode": knowledge_base["profile_mode"],
                        "chunk_size_tokens": knowledge_base["chunk_size_tokens"],
                        "chunk_overlap_tokens": knowledge_base["chunk_overlap_tokens"],
                        "chunk_keyword_limit": knowledge_base["chunk_keyword_limit"],
                        "document_keyword_limit": knowledge_base["document_keyword_limit"],
                    },
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

    def get_document_index_stats(self, document_id: str) -> dict:
        document = self.document_service.get_document(document_id)
        summary = self.api_service.get_document_index_summary(document_id)
        chunks_count = int(summary.get("chunks_count") or 0)
        jobs = [job for job in self.job_store.list_jobs() if job.get("document_id") == document_id]
        jobs.sort(key=lambda item: item.get("started_at") or "", reverse=True)
        latest_job = jobs[0] if jobs else None
        return {
            "document_id": document_id,
            "status": document.status,
            "chunks_count": chunks_count,
            "keywords": list(summary.get("keywords") or []),
            "document_keywords": list(summary.get("document_keywords") or []),
            "index_profile": summary.get("index_profile"),
            "latest_job": latest_job,
        }

    def get_document_chunks(self, document_id: str) -> dict:
        document = self.document_service.get_document(document_id)
        return {
            "document_id": document_id,
            "file_name": document.file_name,
            "chunks": self.api_service.get_document_chunks(document_id),
        }

    def cleanup_orphan_chunks(self, dry_run: bool = True) -> dict:
        indexed_ids = set(self.api_service.list_indexed_document_ids())
        existing_ids = {item["document_id"] for item in self.document_service.list_documents()}
        orphan_ids = sorted(indexed_ids - existing_ids)

        deleted_documents = 0
        if not dry_run:
            for orphan_id in orphan_ids:
                self.api_service.delete_document_chunks(orphan_id)
                deleted_documents += 1

        return {
            "dry_run": bool(dry_run),
            "indexed_documents_count": len(indexed_ids),
            "existing_documents_count": len(existing_ids),
            "orphan_document_ids": orphan_ids,
            "deleted_documents_count": deleted_documents,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
