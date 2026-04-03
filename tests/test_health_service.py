import unittest
from unittest.mock import patch

from backend.services.health_service import HealthService


class _QdrantClientOk:
    def get_collection(self, _name):
        return {}


class _QdrantServiceOk:
    collection_name = "test"
    client = _QdrantClientOk()


class _StorageOk:
    def save(self, _key, _value):
        return None

    def read(self, _key):
        return b"ok"


class HealthServiceLLMConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.service = HealthService(qdrant_service=_QdrantServiceOk(), storage=_StorageOk())

    @patch("backend.services.health_service.Config.LLM_PROVIDER", "openrouter")
    @patch("backend.services.health_service.Config.OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    @patch("backend.services.health_service.Config.OPENROUTER_MODEL", "openai/gpt-4o-mini")
    @patch("backend.services.health_service.Config.OPENROUTER_API_KEY", "")
    def test_ready_is_degraded_when_openrouter_api_key_missing(self):
        payload, ready = self.service.ready()
        self.assertFalse(ready)
        self.assertEqual(payload["status"], "degraded")
        self.assertFalse(payload["checks"]["llm"])
        self.assertEqual(payload["meta"]["llm_provider"], "openrouter")

    @patch("backend.services.health_service.Config.LLM_PROVIDER", "openrouter")
    @patch("backend.services.health_service.Config.OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    @patch("backend.services.health_service.Config.OPENROUTER_MODEL", "openai/gpt-4o-mini")
    @patch("backend.services.health_service.Config.OPENROUTER_API_KEY", "or-key")
    def test_ready_is_ok_when_openrouter_config_is_complete(self):
        payload, ready = self.service.ready()
        self.assertTrue(ready)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["checks"]["llm"])
        self.assertEqual(payload["meta"]["llm_provider"], "openrouter")

    @patch("backend.services.health_service.Config.LLM_PROVIDER", "local")
    @patch("backend.services.health_service.Config.LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    @patch("backend.services.health_service.Config.LOCAL_LLM_MODEL", "qwen2.5:14b")
    def test_ready_is_ok_for_local_llm_without_api_key(self):
        payload, ready = self.service.ready()
        self.assertTrue(ready)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["checks"]["llm"])
        self.assertEqual(payload["meta"]["llm_provider"], "local")

    @patch("backend.services.health_service.Config.LLM_PROVIDER", "unknown")
    def test_ready_is_degraded_for_unsupported_provider(self):
        payload, ready = self.service.ready()
        self.assertFalse(ready)
        self.assertEqual(payload["status"], "degraded")
        self.assertFalse(payload["checks"]["llm"])
        self.assertEqual(payload["meta"]["llm_provider"], "unknown")


if __name__ == "__main__":
    unittest.main()
