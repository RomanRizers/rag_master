from __future__ import annotations

from backend.core.exceptions import StorageError
from backend.infrastructure.qdrant.client import QdrantService
from backend.infrastructure.storage import StorageAdapter, create_storage_adapter


class HealthService:
    def __init__(self, qdrant_service: QdrantService | None = None, storage: StorageAdapter | None = None):
        self.qdrant_service = qdrant_service or QdrantService()
        self.storage = storage or create_storage_adapter()

    def live(self) -> dict:
        return {"status": "ok"}

    def ready(self) -> tuple[dict, bool]:
        checks = {
            "qdrant": self._check_qdrant(),
            "storage": self._check_storage(),
        }
        ok = all(checks.values())
        payload = {
            "status": "ok" if ok else "degraded",
            "checks": checks,
        }
        return payload, ok

    def _check_qdrant(self) -> bool:
        try:
            self.qdrant_service.client.get_collection(self.qdrant_service.collection_name)
            return True
        except Exception:
            return False

    def _check_storage(self) -> bool:
        probe_key = "_health/probe.txt"
        try:
            self.storage.save(probe_key, b"ok")
            _ = self.storage.read(probe_key)
            return True
        except StorageError:
            return False
