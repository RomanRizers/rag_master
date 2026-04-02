from __future__ import annotations

from abc import ABC, abstractmethod


class JobStore(ABC):
    @abstractmethod
    def create_job(self, job: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_job(self, job_id: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def update_job(self, job_id: str, **changes) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_jobs(self) -> list[dict]:
        raise NotImplementedError
