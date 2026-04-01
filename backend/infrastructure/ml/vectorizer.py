from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import torch.nn.functional as F
from backend.core.config import Config
from backend.core.exceptions import VectorizationError
import structlog

logger = structlog.get_logger("vectorizer")

class TextVectorizer:
    def __init__(self, model_name=None):
        """Инициализирует токенизатор и модель для использования e5-base-en-ru с Hugging Face."""
        self.model_name = model_name or Config.MODEL_NAME
        logger.info("vectorizer_model_loading", model_name=self.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()
        logger.info("vectorizer_model_loaded", model_name=self.model_name)

    def vectorize_text(self, text: str) -> np.ndarray:
        """Векторизует текст и возвращает нормализованный вектор."""
        if not isinstance(text, str) or not text.strip():
            raise VectorizationError(message="Input text must be a non-empty string", code="invalid_vectorization_input", status_code=400)

        try:
            logger.debug("vectorize_text_started", model_name=self.model_name, text_length=len(text))
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)

            with torch.no_grad():
                embeddings = self.model(**inputs).last_hidden_state

            mean_embedding = embeddings.mean(dim=1)
            normalized_embedding = F.normalize(mean_embedding, p=2, dim=1)
            vector = normalized_embedding.squeeze().numpy()
            logger.debug("vectorize_text_finished", vector_size=int(vector.shape[0]))
            return vector
        except VectorizationError:
            raise
        except Exception as error:
            raise VectorizationError(details={"reason": str(error), "model_name": self.model_name}) from error
