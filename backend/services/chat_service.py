from datetime import datetime, timezone
import re
from typing import Iterator
from threading import RLock
from uuid import uuid4

from backend.core.config import Config
from backend.core.exceptions import ValidationError
from backend.infrastructure.chat_store import ChatStore, create_chat_store
from backend.infrastructure.llm import create_llm_provider
from backend.services.api_service import ApiService

DEFAULT_SYSTEM_PROMPT = (
    "Ты помощник в RAG-системе. Отвечай по существу и используй только доступный контекст. "
    "Если данных недостаточно, явно скажи об этом."
)


class ChatService:
    def __init__(self, llm_provider=None, retriever=None, chat_store: ChatStore | None = None):
        self.llm_provider = llm_provider or create_llm_provider()
        self.retriever = retriever or _default_retriever
        self.chat_store = chat_store or create_chat_store()
        self._lock = RLock()

    def create_session(self) -> dict:
        session_id = str(uuid4())
        created_at = _now_iso()
        return self.chat_store.create_session(session_id=session_id, created_at=created_at)

    def list_sessions(self) -> list[dict]:
        return self.chat_store.list_sessions()

    def get_messages(self, session_id: str) -> list[dict]:
        messages = self.chat_store.get_messages(session_id)
        if messages is None:
            self._raise_session_not_found(session_id)
        return messages

    def delete_session(self, session_id: str) -> dict:
        deleted = self.chat_store.delete_session(session_id)
        if deleted is None:
            self._raise_session_not_found(session_id)
        return deleted

    def send_message(
        self,
        session_id: str,
        message: str,
        top_k: int | None = None,
        keywords: list[str] | None = None,
        filters: dict | None = None,
    ) -> tuple[dict, dict]:
        with self._lock:
            history = self.chat_store.get_messages(session_id)
            if history is None:
                self._raise_session_not_found(session_id)

            user_message = {
                "id": str(uuid4()),
                "role": "user",
                "content": message.strip(),
                "citations": [],
                "created_at": _now_iso(),
            }
            self.chat_store.append_message(session_id, user_message)
            history.append(user_message)

            effective_top_k = top_k or Config.TOP_K_DEFAULT
            retrieval = self.retriever(message.strip(), effective_top_k, keywords, filters)
            search_results = retrieval.get("results", [])
            filtered_results = _apply_search_filters(search_results, filters)
            selected_results = _select_context_results(message.strip(), filtered_results)

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
            self.chat_store.append_message(session_id, assistant_message)

            return user_message, assistant_message

    def stream_message(
        self,
        session_id: str,
        message: str,
        top_k: int | None = None,
        keywords: list[str] | None = None,
        filters: dict | None = None,
    ) -> tuple[dict, list[dict], Iterator[str]]:
        clean_message = message.strip()
        with self._lock:
            history = self.chat_store.get_messages(session_id)
            if history is None:
                self._raise_session_not_found(session_id)

            user_message = {
                "id": str(uuid4()),
                "role": "user",
                "content": clean_message,
                "citations": [],
                "created_at": _now_iso(),
            }
            self.chat_store.append_message(session_id, user_message)
            history.append(user_message)
            llm_history = list(history)

        effective_top_k = top_k or Config.TOP_K_DEFAULT
        retrieval = self.retriever(clean_message, effective_top_k, keywords, filters)
        search_results = retrieval.get("results", [])
        filtered_results = _apply_search_filters(search_results, filters)
        selected_results = _select_context_results(clean_message, filtered_results)
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
                persisted = self.chat_store.append_message(session_id, assistant_message)
                if not persisted:
                    self._raise_session_not_found(session_id)

        return user_message, citations, token_stream()

    @staticmethod
    def _raise_session_not_found(session_id: str):
        raise ValidationError(
            message=f"Chat session not found: {session_id}",
            code="session_not_found",
            status_code=404,
        )

    def close(self):
        close_fn = getattr(self.chat_store, "close", None)
        if callable(close_fn):
            close_fn()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_retriever(query: str, top_k: int, keywords: list[str] | None, filters: dict | None = None):
    return ApiService().search_query(query, top_k=top_k, keywords=keywords)


def _apply_search_filters(search_results: list[dict], filters: dict | None) -> list[dict]:
    if not filters:
        return search_results

    document_names = {
        str(item).strip().lower()
        for item in (filters.get("document_names") or [])
        if isinstance(item, str) and item.strip()
    }
    tags = {
        str(item).strip().lower()
        for item in (filters.get("tags") or [])
        if isinstance(item, str) and item.strip()
    }
    knowledge_bases = {
        str(item).strip().lower()
        for item in (filters.get("knowledge_bases") or [])
        if isinstance(item, str) and item.strip()
    }
    if not document_names and not tags and not knowledge_bases:
        return search_results

    filtered = []
    for item in search_results:
        payload = item.get("payload") or {}

        if document_names:
            current_name = str(payload.get("document_name") or "").strip().lower()
            if current_name not in document_names:
                continue

        if tags:
            payload_tags = payload.get("tags") or []
            if isinstance(payload_tags, str):
                payload_tags = [payload_tags]
            normalized_tags = {
                str(tag).strip().lower()
                for tag in payload_tags
                if isinstance(tag, str) and tag.strip()
            }
            if not normalized_tags.intersection(tags):
                continue

        if knowledge_bases:
            current_base = str(payload.get("knowledge_base") or "").strip().lower()
            if current_base not in knowledge_bases:
                continue

        filtered.append(item)
    return filtered


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
