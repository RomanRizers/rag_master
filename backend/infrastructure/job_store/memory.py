from __future__ import annotations

from threading import RLock

from backend.infrastructure.job_store.base import JobStore


class InMemoryJobStore(JobStore):
    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = RLock()

    def create_job(self, job: dict) -> dict:
        with self._lock:
            self._jobs[job["job_id"]] = dict(job)
            return dict(self._jobs[job["job_id"]])

    def get_job(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job is not None else None

    def update_job(self, job_id: str, **changes) -> dict:
        with self._lock:
            job = self._jobs[job_id]
            job.update(changes)
            return dict(job)

    def list_jobs(self) -> list[dict]:
        with self._lock:
            return [dict(item) for item in self._jobs.values()]

    def claim_next_queued(self, started_at: str) -> dict | None:
        with self._lock:
            for job in self._jobs.values():
                if job.get("status") == "queued":
                    job["status"] = "running"
                    job["started_at"] = job.get("started_at") or started_at
                    return dict(job)
        return None
