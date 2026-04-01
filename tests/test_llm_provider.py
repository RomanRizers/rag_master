import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from backend.core.exceptions import LLMError
from backend.infrastructure.llm.provider import (
    LocalLLMProvider,
    OpenRouterProvider,
    create_llm_provider,
)


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LLMProviderFactoryTestCase(unittest.TestCase):
    @patch("backend.infrastructure.llm.provider.Config.LLM_PROVIDER", "openrouter")
    def test_factory_returns_openrouter_provider(self):
        provider = create_llm_provider()
        self.assertIsInstance(provider, OpenRouterProvider)

    @patch("backend.infrastructure.llm.provider.Config.LLM_PROVIDER", "local")
    def test_factory_returns_local_provider(self):
        provider = create_llm_provider()
        self.assertIsInstance(provider, LocalLLMProvider)

    @patch("backend.infrastructure.llm.provider.Config.LLM_PROVIDER", "unknown")
    def test_factory_raises_for_unknown_provider(self):
        with self.assertRaises(LLMError) as context:
            create_llm_provider()
        self.assertEqual(context.exception.code, "invalid_llm_provider")


class OpenRouterProviderTestCase(unittest.TestCase):
    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_MODEL", "openrouter/test-model")
    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_API_KEY", "token")
    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_BASE_URL", "https://test.openrouter.ai/api/v1")
    @patch(
        "backend.infrastructure.llm.provider.request.urlopen",
        return_value=_Response({"choices": [{"message": {"content": "hello"}}]}),
    )
    def test_generate_returns_message_content(self, _urlopen):
        provider = OpenRouterProvider()
        value = provider.generate([{"role": "user", "content": "hi"}])
        self.assertEqual(value, "hello")

    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_MODEL", "openrouter/test-model")
    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_API_KEY", "token")
    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_BASE_URL", "https://test.openrouter.ai/api/v1")
    @patch(
        "backend.infrastructure.llm.provider.request.urlopen",
        return_value=_Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "first"},
                                {"type": "text", "text": "second"},
                            ]
                        }
                    }
                ]
            }
        ),
    )
    def test_generate_supports_multimodal_content_list(self, _urlopen):
        provider = OpenRouterProvider()
        value = provider.generate([{"role": "user", "content": "hi"}])
        self.assertEqual(value, "first\nsecond")

    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_MODEL", "openrouter/test-model")
    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_API_KEY", "token")
    @patch("backend.infrastructure.llm.provider.Config.OPENROUTER_BASE_URL", "https://test.openrouter.ai/api/v1")
    @patch(
        "backend.infrastructure.llm.provider.request.urlopen",
        side_effect=HTTPError(
            url="https://test.openrouter.ai/api/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"auth"}'),
        ),
    )
    def test_generate_maps_http_error_to_llm_error(self, _urlopen):
        provider = OpenRouterProvider()
        with self.assertRaises(LLMError) as context:
            provider.generate([{"role": "user", "content": "hi"}])
        self.assertEqual(context.exception.code, "llm_request_failed")


if __name__ == "__main__":
    unittest.main()
