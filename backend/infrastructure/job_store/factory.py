from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.job_store.base import JobStore
from backend.infrastructure.job_store.memory import InMemoryJobStore
from backend.infrastructure.job_store.postgres import PostgresJobStore


def create_job_store() -> JobStore:
    backend = Config.JOB_STORE_BACKEND
    if backend == "memory":
        return InMemoryJobStore()
    if backend == "postgres":
        if not Config.POSTGRES_DSN:
            raise ValidationError(
                message="POSTGRES_DSN is required when JOB_STORE_BACKEND=postgres",
                code="invalid_job_store_config",
            )
        return PostgresJobStore(dsn=Config.POSTGRES_DSN)
    raise ValidationError(
        message=f"Unsupported job store backend: {backend}",
        code="invalid_job_store_backend",
    )
