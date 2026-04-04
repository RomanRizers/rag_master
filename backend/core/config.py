import os


class Config:
    """Класс для хранения конфигурации приложения."""
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "gazprom_dataset_e5")
    MODEL_NAME = os.getenv("MODEL_NAME", "d0rj/e5-base-en-ru")
    TOP_K_DEFAULT = int(os.getenv("TOP_K_DEFAULT", "5"))
    TOP_K_MAX = int(os.getenv("TOP_K_MAX", "50"))
    CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "600"))
    CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "120"))
    RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "8"))
    RERANK_SEMANTIC_WEIGHT = float(os.getenv("RERANK_SEMANTIC_WEIGHT", "0.7"))
    CHAT_MAX_CONTEXT_CHARS = int(os.getenv("CHAT_MAX_CONTEXT_CHARS", "6000"))
    CHAT_STORE_BACKEND = os.getenv("CHAT_STORE_BACKEND", "memory").strip().lower()
    JOB_STORE_BACKEND = os.getenv("JOB_STORE_BACKEND", "memory").strip().lower()

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()

    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")

    LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "")
    LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "")

    LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "60"))
    HEALTHCHECK_LLM_ACTIVE_PROBE = os.getenv("HEALTHCHECK_LLM_ACTIVE_PROBE", "0").strip() in {"1", "true", "yes"}
    HEALTHCHECK_LLM_TIMEOUT_SECONDS = float(os.getenv("HEALTHCHECK_LLM_TIMEOUT_SECONDS", "2.0"))

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    DOCUMENTS_STORAGE_PATH = os.getenv("DOCUMENTS_STORAGE_PATH", "/tmp/rag_documents")
    DOCUMENT_STORE_BACKEND = os.getenv("DOCUMENT_STORE_BACKEND", "memory").strip().lower()
    POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://rag:rag@postgres:5432/rag").strip()
    INGESTION_WORKER_POLL_SECONDS = float(os.getenv("INGESTION_WORKER_POLL_SECONDS", "1.0"))
    INGESTION_RETRY_BACKOFF_SECONDS = float(os.getenv("INGESTION_RETRY_BACKOFF_SECONDS", "0.5"))
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1").strip() in {"1", "true", "yes"}
    RATE_LIMIT_UPLOAD_RPM = int(os.getenv("RATE_LIMIT_UPLOAD_RPM", "30"))
    RATE_LIMIT_INDEXING_RPM = int(os.getenv("RATE_LIMIT_INDEXING_RPM", "60"))
    RATE_LIMIT_CHAT_RPM = int(os.getenv("RATE_LIMIT_CHAT_RPM", "120"))
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me").strip()

    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "").strip()
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "").strip()
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "").strip()
    S3_BUCKET = os.getenv("S3_BUCKET", "rag-documents").strip()
    S3_REGION = os.getenv("S3_REGION", "us-east-1").strip()
    S3_AUTO_CREATE_BUCKET = os.getenv("S3_AUTO_CREATE_BUCKET", "1").strip() in {"1", "true", "yes"}
