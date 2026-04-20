from __future__ import annotations

import threading

import numpy as np
import structlog
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from backend.core.config import Config
from backend.core.exceptions import VectorizationError

logger = structlog.get_logger("vectorizer")


class TextVectorizer:
    def __init__(self, model_name=None):
        self.model_name = model_name or Config.MODEL_NAME
        logger.info("vectorizer_model_loading", model_name=self.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()
        self._lock = threading.Lock()
        logger.info("vectorizer_model_loaded", model_name=self.model_name)

    def vectorize_text(self, text: str, prefix: str = "") -> np.ndarray:
        if not isinstance(text, str) or not text.strip():
            raise VectorizationError(
                message="Input text must be a non-empty string",
                code="invalid_vectorization_input",
                status_code=400,
            )
        return self.vectorize_batch([text], prefix=prefix)[0]

    def vectorize_batch(self, texts: list[str], prefix: str = "") -> list[np.ndarray]:
        """Векторизует список текстов за один forward pass.

        Использует Lock для thread-safety: PyTorch не гарантирует
        корректность при одновременных вызовах из нескольких потоков.
        """
        if not texts:
            return []
        try:
            prefixed = [prefix + t for t in texts] if prefix else texts
            logger.debug("vectorize_batch_started", model_name=self.model_name, batch_size=len(prefixed))
            with self._lock:
                inputs = self.tokenizer(
                    prefixed,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512,
                )
                with torch.no_grad():
                    embeddings = self.model(**inputs).last_hidden_state

            # CLS token pooling (index 0) — required for BGE-M3 and compatible with E5
            cls_embeddings = embeddings[:, 0, :]
            normalized = F.normalize(cls_embeddings, p=2, dim=1)
            vectors = [normalized[i].numpy() for i in range(len(texts))]
            logger.debug("vectorize_batch_finished", batch_size=len(texts), vector_size=int(vectors[0].shape[0]))
            return vectors
        except VectorizationError:
            raise
        except Exception as error:
            raise VectorizationError(details={"reason": str(error), "model_name": self.model_name}) from error

    def encode_for_chunking(self, text: str) -> list[int]:
        if not isinstance(text, str) or not text.strip():
            return []
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode_tokens(self, token_ids: list[int]) -> str:
        if not token_ids:
            return ""
        return self.tokenizer.decode(token_ids, skip_special_tokens=True).strip()

    def count_tokens(self, text: str) -> int:
        return len(self.encode_for_chunking(text))
