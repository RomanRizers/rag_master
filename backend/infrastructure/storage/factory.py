from backend.core.config import Config
from backend.core.exceptions import StorageError
from backend.infrastructure.storage.base import StorageAdapter
from backend.infrastructure.storage.local import LocalFileStorageAdapter
from backend.infrastructure.storage.s3 import S3StorageAdapter


def create_storage_adapter() -> StorageAdapter:
    backend = Config.STORAGE_BACKEND
    if backend == "local":
        return LocalFileStorageAdapter(root_path=Config.DOCUMENTS_STORAGE_PATH)
    if backend == "s3":
        return S3StorageAdapter.from_config()

    raise StorageError(
        message=f"Unsupported storage backend: {backend}",
        code="storage_error",
        status_code=500,
    )
