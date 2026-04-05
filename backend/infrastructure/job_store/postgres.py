from __future__ import annotations

from datetime import datetime
from threading import RLock

import psycopg

from backend.infrastructure.job_store.base import JobStore


class PostgresJobStore(JobStore):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._lock = RLock()
        self._conn = psycopg.connect(dsn)
        self._conn.autocommit = True

    def create_job(self, job: dict) -> dict:
        query = """
            INSERT INTO ingestion_jobs(
                job_id, document_id, status, progress, attempt, error_code, error_message, started_at, finished_at
            )
            VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz)
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                query,
                (
                    job["job_id"],
                    job["document_id"],
                    job["status"],
                    int(job["progress"]),
                    int(job.get("attempt", 0)),
                    job.get("error_code"),
                    job.get("error_message"),
                    job.get("started_at"),
                    job.get("finished_at"),
                ),
            )
        return self.get_job(job["job_id"]) or dict(job)

    def get_job(self, job_id: str) -> dict | None:
        query = """
            SELECT job_id, document_id, status, progress, attempt, error_code, error_message, started_at, finished_at
            FROM ingestion_jobs
            WHERE job_id = %s::uuid
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (job_id,))
            row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_job(row)

    def update_job(self, job_id: str, **changes) -> dict:
        current = self.get_job(job_id)
        if current is None:
            raise KeyError(job_id)
        updated = dict(current)
        updated.update(changes)
        query = """
            UPDATE ingestion_jobs
            SET status = %s, progress = %s, attempt = %s, error_code = %s, error_message = %s, started_at = %s::timestamptz, finished_at = %s::timestamptz
            WHERE job_id = %s::uuid
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                query,
                (
                    updated["status"],
                    int(updated["progress"]),
                    int(updated.get("attempt", 0)),
                    updated.get("error_code"),
                    updated.get("error_message"),
                    updated.get("started_at"),
                    updated.get("finished_at"),
                    job_id,
                ),
            )
        return updated

    def list_jobs(self) -> list[dict]:
        query = """
            SELECT job_id, document_id, status, progress, attempt, error_code, error_message, started_at, finished_at
            FROM ingestion_jobs
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return [_row_to_job(row) for row in rows]

    def claim_next_queued(self, started_at: str) -> dict | None:
        query = """
            WITH picked AS (
                SELECT job_id
                FROM ingestion_jobs
                WHERE status = 'queued'
                ORDER BY job_id
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE ingestion_jobs AS jobs
            SET status = 'running',
                started_at = COALESCE(jobs.started_at, %s::timestamptz)
            FROM picked
            WHERE jobs.job_id = picked.job_id
            RETURNING
                jobs.job_id,
                jobs.document_id,
                jobs.status,
                jobs.progress,
                jobs.attempt,
                jobs.error_code,
                jobs.error_message,
                jobs.started_at,
                jobs.finished_at
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (started_at,))
            row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_job(row)

    def delete_jobs_for_document(self, document_id: str) -> int:
        query = """
            DELETE FROM ingestion_jobs
            WHERE document_id = %s::uuid
        """
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(query, (document_id,))
            return cursor.rowcount or 0

    def close(self):
        with self._lock:
            self._conn.close()


def _row_to_job(row: tuple) -> dict:
    return {
        "job_id": str(row[0]),
        "document_id": str(row[1]),
        "status": row[2],
        "progress": int(row[3]),
        "attempt": int(row[4]),
        "error_code": row[5],
        "error_message": row[6],
        "started_at": _to_iso(row[7]),
        "finished_at": _to_iso(row[8]),
    }


def _to_iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
