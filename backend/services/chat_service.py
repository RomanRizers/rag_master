from datetime import datetime, timezone
import re
from typing import Iterator
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
        self._session_meta: dict[str, dict] = {}
        self._lock = RLock()

    def create_session(self) -> dict:
        session_id = str(uuid4())
        created_at = _now_iso()
        with self._lock:
            self._sessions[session_id] = []
            self._session_meta[session_id] = {"session_id": session_id, "created_at": created_at}
        return {"session_id": session_id, "created_at": created_at}

    def list_sessions(self) -> list[dict]:
        with self._lock:
            items = []
            for session_id, meta in self._session_meta.items():
                history = self._sessions.get(session_id, [])
                last_created_at = history[-1]["created_at"] if history else None
                items.append(
                    {
                        "session_id": session_id,
                        "created_at": meta["created_at"],
                        "message_count": len(history),
                        "last_message_at": last_created_at,
                    }
                )
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items

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
            selected_results = _select_context_results(message.strip(), search_results)

            context = _build_context(selected_results, Config.CHAT_MAX_CONTEXT_CHARS)
            citations = _build_citations(selected_results)

            llm_messages = _build_llm_messages(history, context)

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

    def stream_message(
        self,
        session_id: str,
        message: str,
        top_k: int | None = None,
        keywords: list[str] | None = None,
    ) -> tuple[dict, list[dict], Iterator[str]]:
        clean_message = message.strip()
        with self._lock:
            history = self._sessions.get(session_id)
            if history is None:
                self._raise_session_not_found(session_id)

            user_message = {
                "id": str(uuid4()),
                "role": "user",
                "content": clean_message,
                "citations": [],
                "created_at": _now_iso(),
            }
            history.append(user_message)
            llm_history = list(history)

        effective_top_k = top_k or Config.TOP_K_DEFAULT
        retrieval = self.retriever(clean_message, effective_top_k, keywords)
        search_results = retrieval.get("results", [])
        selected_results = _select_context_results(clean_message, search_results)
        context = _build_context(selected_results, Config.CHAT_MAX_CONTEXT_CHARS)
        citations = _build_citations(selected_results)
        llm_messages = _build_llm_messages(llm_history, context)

        def token_stream():
            chunks = []
            for delta in self.llm_provider.stream_chat(llm_messages):
                chunks.append(delta)
                yield delta

            assistant_message = {
                "id": str(uuid4()),
                "role": "assistant",
                "content": "".join(chunks).strip(),
                "citations": citations,
                "created_at": _now_iso(),
            }
            with self._lock:
                latest_history = self._sessions.get(session_id)
                if latest_history is None:
                    self._raise_session_not_found(session_id)
                latest_history.append(assistant_message)

        return user_message, citations, token_stream()

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


def _build_context(search_results: list[dict], max_chars: int) -> str:
    context_parts = []
    total_len = 0
    for index, item in enumerate(search_results, start=1):
        payload = item.get("payload") or {}
        content = str(payload.get("content") or "").strip()
        if not content:
            continue
        part = f"[{index}] {content}"
        projected_len = total_len + len(part) + (2 if context_parts else 0)
        if projected_len > max_chars:
            break
        context_parts.append(part)
        total_len = projected_len
    return "\n\n".join(context_parts)


def _build_llm_messages(history: list[dict], context: str) -> list[dict[str, str]]:
    llm_messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    llm_messages.extend(
        {"role": item["role"], "content": item["content"]}
        for item in history
        if item["role"] in {"user", "assistant"}
    )
    if context:
        llm_messages.append({"role": "system", "content": f"Контекст для ответа:\n{context}"})
    return llm_messages


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


def _select_context_results(query: str, search_results: list[dict]) -> list[dict]:
    reranked = _rerank_results(query, search_results)
    limit = max(1, Config.RERANK_TOP_N)
    return reranked[:limit]


def _rerank_results(query: str, search_results: list[dict]) -> list[dict]:
    semantic_weight = min(1.0, max(0.0, Config.RERANK_SEMANTIC_WEIGHT))
    lexical_weight = 1.0 - semantic_weight
    query_tokens = set(_tokenize(query))
    max_semantic = _max_semantic_score(search_results)

    def rank_key(item: dict) -> tuple[float, float, str]:
        payload = item.get("payload") or {}
        content = str(payload.get("content") or "")
        lexical_score = _lexical_overlap_score(query_tokens, content)
        semantic_score = _normalized_semantic_score(item, max_semantic)
        combined = semantic_weight * semantic_score + lexical_weight * lexical_score
        stable_id = str(item.get("id") or "")
        return combined, semantic_score, stable_id

    return sorted(search_results, key=rank_key, reverse=True)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zа-яА-Я0-9]+", text.lower())


def _lexical_overlap_score(query_tokens: set[str], content: str) -> float:
    if not query_tokens:
        return 0.0
    content_tokens = set(_tokenize(content))
    if not content_tokens:
        return 0.0
    overlap = query_tokens.intersection(content_tokens)
    return len(overlap) / float(len(query_tokens))


def _max_semantic_score(search_results: list[dict]) -> float:
    max_score = 0.0
    for item in search_results:
        max_score = max(max_score, _safe_float(item.get("score")))
    return max_score


def _normalized_semantic_score(item: dict, max_semantic: float) -> float:
    score = _safe_float(item.get("score"))
    if max_semantic > 0:
        return score / max_semantic
    return score


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
