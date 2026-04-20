import os


class Config:
    """Класс для хранения конфигурации приложения."""
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "rag_bge_m3")
    MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-m3")
    TOP_K_DEFAULT = int(os.getenv("TOP_K_DEFAULT", "5"))
    TOP_K_MAX = int(os.getenv("TOP_K_MAX", "50"))
    CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "600"))
    CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "120"))
    DENSE_RETRIEVE_TOP_N = int(os.getenv("DENSE_RETRIEVE_TOP_N", "40"))
    SPARSE_RETRIEVE_TOP_N = int(os.getenv("SPARSE_RETRIEVE_TOP_N", "40"))
    FUSED_RETRIEVE_TOP_N = int(os.getenv("FUSED_RETRIEVE_TOP_N", "20"))
    RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "8"))
    RERANK_SEMANTIC_WEIGHT = float(os.getenv("RERANK_SEMANTIC_WEIGHT", "0.62"))
    RERANK_LEXICAL_WEIGHT = float(os.getenv("RERANK_LEXICAL_WEIGHT", "0.15"))
    RERANK_KEYWORD_WEIGHT = float(os.getenv("RERANK_KEYWORD_WEIGHT", "0.08"))
    RERANK_METADATA_WEIGHT = float(os.getenv("RERANK_METADATA_WEIGHT", "0.15"))
    CHAT_MAX_CONTEXT_CHARS = int(os.getenv("CHAT_MAX_CONTEXT_CHARS", "12000"))
    CHAT_MAX_CONTEXT_TOKENS = int(os.getenv("CHAT_MAX_CONTEXT_TOKENS", "2800"))
    CHAT_HISTORY_MAX_MESSAGES = int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", "8"))
    CHAT_MIN_RESULTS_REQUIRED = int(os.getenv("CHAT_MIN_RESULTS_REQUIRED", "1"))
    CHAT_MIN_RERANK_SCORE = float(os.getenv("CHAT_MIN_RERANK_SCORE", "0.20"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1400"))
    # E5 model inference prefixes — set to "query: " / "passage: " when using E5-family models.
    # Changing E5_PASSAGE_PREFIX requires full re-indexing of all documents.
    E5_QUERY_PREFIX = os.getenv("E5_QUERY_PREFIX", "")   # leave empty for BGE-M3
    E5_PASSAGE_PREFIX = os.getenv("E5_PASSAGE_PREFIX", "")  # leave empty for BGE-M3
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
