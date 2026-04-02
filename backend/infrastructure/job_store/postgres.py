from __future__ import annotations

from threading import RLock

import psycopg

from backend.infrastructure.job_store.base import JobStore


class PostgresJobStore(JobStore):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._lock = RLock()
        self._conn = psycopg.connect(dsn)
        self._conn.autocommit = True
        self._ensure_schema()

    def create_job(self, job: dict) -> dict:
        query = """
            INSERT INTO ingestion_jobs(
                job_id, document_id, status, progress, attempt, error_code, error_message, started_at, finished_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            WHERE job_id = %s
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
            SET status = %s, progress = %s, attempt = %s, error_code = %s, error_message = %s, started_at = %s, finished_at = %s
            WHERE job_id = %s
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

    def _ensure_schema(self):
        with self._lock, self._conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_jobs(
                    job_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    error_message TEXT,
                    started_at TEXT,
                    finished_at TEXT
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_document_id ON ingestion_jobs(document_id)"
            )

    def close(self):
        with self._lock:
            self._conn.close()


def _row_to_job(row: tuple) -> dict:
    return {
        "job_id": row[0],
        "document_id": row[1],
        "status": row[2],
        "progress": int(row[3]),
        "attempt": int(row[4]),
        "error_code": row[5],
        "error_message": row[6],
        "started_at": row[7],
        "finished_at": row[8],
    }
