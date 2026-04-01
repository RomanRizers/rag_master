from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.llm import create_llm_provider
from backend.services.api_service import ApiService

DEFAULT_SYSTEM_PROMPT = (
    "Ты помощник в RAG-системе. Отвечай по существу и используй только доступный контекст. "
    "Если данных недостаточно, явно скажи об этом."
)


class ChatService:
    def __init__(self, llm_provider=None, retriever=None):
        self.llm_provider = llm_provider or create_llm_provider()
        self.retriever = retriever or _default_retriever
        self._sessions: dict[str, list[dict]] = {}
        self._lock = RLock()

    def create_session(self) -> dict:
        session_id = str(uuid4())
        created_at = _now_iso()
        with self._lock:
            self._sessions[session_id] = []
        return {"session_id": session_id, "created_at": created_at}

    def get_messages(self, session_id: str) -> list[dict]:
        with self._lock:
            messages = self._sessions.get(session_id)
            if messages is None:
                self._raise_session_not_found(session_id)
            return list(messages)

    def send_message(
        self,
        session_id: str,
        message: str,
        top_k: int | None = None,
        keywords: list[str] | None = None,
    ) -> tuple[dict, dict]:
        with self._lock:
            history = self._sessions.get(session_id)
            if history is None:
                self._raise_session_not_found(session_id)

            user_message = {
                "id": str(uuid4()),
                "role": "user",
                "content": message.strip(),
                "citations": [],
                "created_at": _now_iso(),
            }
            history.append(user_message)

            effective_top_k = top_k or Config.TOP_K_DEFAULT
            retrieval = self.retriever(message.strip(), effective_top_k, keywords)
            search_results = retrieval.get("results", [])

            context = _build_context(search_results)
            citations = _build_citations(search_results)

            llm_messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
            llm_messages.extend(
                {"role": item["role"], "content": item["content"]}
                for item in history
                if item["role"] in {"user", "assistant"}
            )
            if context:
                llm_messages.append({"role": "system", "content": f"Контекст для ответа:\n{context}"})

            assistant_text = self.llm_provider.generate(llm_messages)
            assistant_message = {
                "id": str(uuid4()),
                "role": "assistant",
                "content": assistant_text,
                "citations": citations,
                "created_at": _now_iso(),
            }
            history.append(assistant_message)

            return user_message, assistant_message

    @staticmethod
    def _raise_session_not_found(session_id: str):
        raise ValidationError(
            message=f"Chat session not found: {session_id}",
            code="session_not_found",
            status_code=404,
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_retriever(query: str, top_k: int, keywords: list[str] | None):
    return ApiService().search_query(query, top_k=top_k, keywords=keywords)


def _build_context(search_results: list[dict]) -> str:
    context_parts = []
    for index, item in enumerate(search_results, start=1):
        payload = item.get("payload") or {}
        content = str(payload.get("content") or "").strip()
        if not content:
            continue
        context_parts.append(f"[{index}] {content}")
    return "\n\n".join(context_parts)


def _build_citations(search_results: list[dict]) -> list[dict]:
    citations: list[dict] = []
    for item in search_results:
        payload = item.get("payload") or {}
        content = str(payload.get("content") or "").strip()
        citations.append(
            {
                "document_id": payload.get("document_id"),
                "document_name": payload.get("document_name"),
                "chunk_id": str(item.get("id")) if item.get("id") is not None else None,
                "page": payload.get("page"),
                "snippet": content[:280] if content else None,
            }
        )
    return citations
