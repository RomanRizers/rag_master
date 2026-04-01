import os


class Config:
    """Класс для хранения конфигурации подключения к Qdrant."""
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "gazprom_dataset_e5")
    TOP_K_DEFAULT = int(os.getenv("TOP_K_DEFAULT", "5"))
    TOP_K_MAX = int(os.getenv("TOP_K_MAX", "50"))
