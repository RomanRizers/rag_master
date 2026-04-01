import json
from abc import ABC, abstractmethod
from typing import Any
from urllib import error, request

import structlog

from backend.core.config import Config
from backend.core.exceptions import LLMError

logger = structlog.get_logger("llm")


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 700) -> str:
        """Generates a response using an LLM provider."""


class _OpenAICompatibleProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or ""

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 700) -> str:
        if not self.base_url or not self.model:
            raise LLMError(
                message="LLM provider configuration is incomplete",
                code="invalid_llm_config",
                status_code=500,
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = f"{self.base_url}/chat/completions"
        req = request.Request(endpoint, data=data, headers=headers, method="POST")

        logger.info("llm_request_started", endpoint=endpoint, model=self.model)
        try:
            with request.urlopen(req, timeout=Config.LLM_REQUEST_TIMEOUT_SECONDS) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.warning("llm_http_error", status=exc.code, body=body[:500])
            raise LLMError(
                message="LLM provider request failed",
                code="llm_request_failed",
                details={"status": exc.code, "body": body[:500]},
            ) from exc
        except error.URLError as exc:
            raise LLMError(message="LLM provider is unavailable", code="llm_unavailable") from exc
        except Exception as exc:
            raise LLMError(message="Unexpected LLM provider error", code="llm_unexpected_error") from exc

        content = _extract_message_content(response_data)
        if not content:
            raise LLMError(message="LLM provider returned empty response", code="llm_empty_response")

        logger.info("llm_request_finished", model=self.model, response_length=len(content))
        return content


class OpenRouterProvider(_OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            base_url=Config.OPENROUTER_BASE_URL,
            model=Config.OPENROUTER_MODEL,
            api_key=Config.OPENROUTER_API_KEY,
        )


class LocalLLMProvider(_OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            base_url=Config.LOCAL_LLM_BASE_URL,
            model=Config.LOCAL_LLM_MODEL,
            api_key=Config.LOCAL_LLM_API_KEY,
        )


def create_llm_provider() -> LLMProvider:
    provider = Config.LLM_PROVIDER
    if provider == "openrouter":
        return OpenRouterProvider()
    if provider == "local":
        return LocalLLMProvider()
    raise LLMError(
        message=f"Unsupported LLM provider: {provider}",
        code="invalid_llm_provider",
        status_code=500,
    )


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()

    return ""
