from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.job_store.base import JobStore
from backend.infrastructure.job_store.memory import InMemoryJobStore
from backend.infrastructure.job_store.sqlite import SqliteJobStore


def create_job_store() -> JobStore:
    backend = Config.JOB_STORE_BACKEND
    if backend == "memory":
        return InMemoryJobStore()
    if backend == "sqlite":
        if not Config.JOB_SQLITE_PATH:
            raise ValidationError(
                message="JOB_SQLITE_PATH is required when JOB_STORE_BACKEND=sqlite",
                code="invalid_job_store_config",
            )
        return SqliteJobStore(db_path=Config.JOB_SQLITE_PATH)
    raise ValidationError(
        message=f"Unsupported job store backend: {backend}",
        code="invalid_job_store_backend",
    )
