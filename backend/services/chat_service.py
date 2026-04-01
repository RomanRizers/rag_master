from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from backend.core.exceptions import ValidationError
from backend.infrastructure.llm import create_llm_provider

DEFAULT_SYSTEM_PROMPT = (
    "Ты помощник в RAG-системе. Отвечай по существу и используй только доступный контекст. "
    "Если данных недостаточно, явно скажи об этом."
)


class ChatService:
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider or create_llm_provider()
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

    def send_message(self, session_id: str, message: str) -> tuple[dict, dict]:
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

            llm_messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
            llm_messages.extend(
                {"role": item["role"], "content": item["content"]}
                for item in history
                if item["role"] in {"user", "assistant"}
            )

            assistant_text = self.llm_provider.generate(llm_messages)
            assistant_message = {
                "id": str(uuid4()),
                "role": "assistant",
                "content": assistant_text,
                "citations": [],
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
