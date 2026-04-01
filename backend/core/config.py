import os


class Config:
    """Класс для хранения конфигурации приложения."""
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "gazprom_dataset_e5")
    MODEL_NAME = os.getenv("MODEL_NAME", "d0rj/e5-base-en-ru")
    TOP_K_DEFAULT = int(os.getenv("TOP_K_DEFAULT", "5"))
    TOP_K_MAX = int(os.getenv("TOP_K_MAX", "50"))

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()

    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")

    LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "")
    LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "")

    LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "60"))
