from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock

from backend.infrastructure.job_store.base import JobStore


class SqliteJobStore(JobStore):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def create_job(self, job: dict) -> dict:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ingestion_jobs(
                    job_id, document_id, status, progress, attempt, error_code, error_message, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
            self._conn.commit()
        return self.get_job(job["job_id"]) or dict(job)

    def get_job(self, job_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT job_id, document_id, status, progress, attempt, error_code, error_message, started_at, finished_at
                FROM ingestion_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_job(row)

    def update_job(self, job_id: str, **changes) -> dict:
        current = self.get_job(job_id)
        if current is None:
            raise KeyError(job_id)
        updated = dict(current)
        updated.update(changes)
        with self._lock:
            self._conn.execute(
                """
                UPDATE ingestion_jobs
                SET status = ?, progress = ?, attempt = ?, error_code = ?, error_message = ?, started_at = ?, finished_at = ?
                WHERE job_id = ?
                """,
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
            self._conn.commit()
        return updated

    def list_jobs(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT job_id, document_id, status, progress, attempt, error_code, error_message, started_at, finished_at
                FROM ingestion_jobs
                """
            ).fetchall()
        return [_row_to_job(row) for row in rows]

    def _ensure_schema(self):
        path = Path(self._db_path)
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._conn.execute(
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
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_document_id ON ingestion_jobs(document_id)"
            )
            self._conn.commit()


def _row_to_job(row: sqlite3.Row) -> dict:
    return {
        "job_id": row["job_id"],
        "document_id": row["document_id"],
        "status": row["status"],
        "progress": int(row["progress"]),
        "attempt": int(row["attempt"]),
        "error_code": row["error_code"],
        "error_message": row["error_message"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }
