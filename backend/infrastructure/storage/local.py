from __future__ import annotations

from pathlib import Path

from backend.core.exceptions import StorageError
from backend.infrastructure.storage.base import StorageAdapter


class LocalFileStorageAdapter(StorageAdapter):
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, object_key: str, content: bytes) -> None:
        path = self._resolve_path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(content)
        except Exception as exc:
            raise StorageError(
                message="Failed to save document content",
                code="storage_error",
                details={"object_key": object_key},
            ) from exc

    def read(self, object_key: str) -> bytes:
        path = self._resolve_path(object_key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise StorageError(
                message="Stored document content was not found",
                code="storage_error",
                details={"object_key": object_key},
                status_code=404,
            ) from exc
        except Exception as exc:
            raise StorageError(
                message="Failed to read document content",
                code="storage_error",
                details={"object_key": object_key},
            ) from exc

    def delete(self, object_key: str) -> None:
        path = self._resolve_path(object_key)
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            raise StorageError(
                message="Failed to delete document content",
                code="storage_error",
                details={"object_key": object_key},
            ) from exc

        parent = path.parent
        while parent != self.root and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    def _resolve_path(self, object_key: str) -> Path:
        # Reject absolute paths and traversal components before any filesystem access.
        # Path.resolve() follows symlinks, so a malicious symlink inside root could
        # otherwise escape the storage boundary after the check.
        key = str(object_key or "")
        if not key or key.startswith("/") or any(part in (".", "..") for part in Path(key).parts):
            raise StorageError(
                message="Invalid object key",
                code="storage_error",
                details={"object_key": object_key},
                status_code=400,
            )
        candidate = (self.root / key).resolve()
        root_resolved = self.root.resolve()
        if root_resolved not in candidate.parents and candidate != root_resolved:
            raise StorageError(
                message="Invalid object key",
                code="storage_error",
                details={"object_key": object_key},
                status_code=400,
            )
        return candidate
