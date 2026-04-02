import os


class Config:
    """Класс для хранения конфигурации приложения."""
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "gazprom_dataset_e5")
    MODEL_NAME = os.getenv("MODEL_NAME", "d0rj/e5-base-en-ru")
    TOP_K_DEFAULT = int(os.getenv("TOP_K_DEFAULT", "5"))
    TOP_K_MAX = int(os.getenv("TOP_K_MAX", "50"))
    RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "8"))
    RERANK_SEMANTIC_WEIGHT = float(os.getenv("RERANK_SEMANTIC_WEIGHT", "0.7"))
    CHAT_MAX_CONTEXT_CHARS = int(os.getenv("CHAT_MAX_CONTEXT_CHARS", "6000"))
    CHAT_STORE_BACKEND = os.getenv("CHAT_STORE_BACKEND", "memory").strip().lower()
    CHAT_SQLITE_PATH = os.getenv("CHAT_SQLITE_PATH", "/tmp/rag_chat.db").strip()

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()

    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")

    LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "")
    LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "")

    LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "60"))

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    DOCUMENTS_STORAGE_PATH = os.getenv("DOCUMENTS_STORAGE_PATH", "/tmp/rag_documents")

    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "").strip()
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "").strip()
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "").strip()
    S3_BUCKET = os.getenv("S3_BUCKET", "rag-documents").strip()
    S3_REGION = os.getenv("S3_REGION", "us-east-1").strip()
    S3_AUTO_CREATE_BUCKET = os.getenv("S3_AUTO_CREATE_BUCKET", "1").strip() in {"1", "true", "yes"}
