from __future__ import annotations

from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.core.config import Config
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
            "llm": self._check_llm_config(),
        }
        ok = all(checks.values())
        payload = {
            "status": "ok" if ok else "degraded",
            "checks": checks,
            "meta": {"llm_provider": Config.LLM_PROVIDER},
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

    def _check_llm_config(self) -> bool:
        provider = Config.LLM_PROVIDER
        if provider == "openrouter":
            configured = (
                self._is_http_url(Config.OPENROUTER_BASE_URL)
                and bool(Config.OPENROUTER_MODEL.strip())
                and bool(Config.OPENROUTER_API_KEY.strip())
            )
            if not configured:
                return False
            return self._probe_llm_endpoint(Config.OPENROUTER_BASE_URL, Config.OPENROUTER_API_KEY)
        if provider == "local":
            configured = self._is_http_url(Config.LOCAL_LLM_BASE_URL) and bool(Config.LOCAL_LLM_MODEL.strip())
            if not configured:
                return False
            return self._probe_llm_endpoint(Config.LOCAL_LLM_BASE_URL, Config.LOCAL_LLM_API_KEY)
        return False

    @staticmethod
    def _is_http_url(value: str) -> bool:
        if not value or not value.strip():
            return False
        parsed = urlparse(value.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _probe_llm_endpoint(base_url: str, api_key: str) -> bool:
        if not Config.HEALTHCHECK_LLM_ACTIVE_PROBE:
            return True

        headers = {"Accept": "application/json"}
        if api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        endpoint = f"{base_url.rstrip('/')}/models"
        request = Request(endpoint, method="GET", headers=headers)
        try:
            with urlopen(request, timeout=Config.HEALTHCHECK_LLM_TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", 200)
            return 200 <= int(status) < 300
        except Exception:
            return False
