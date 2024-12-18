from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import torch.nn.functional as F

class TextVectorizer:
    def __init__(self, model_name="d0rj/e5-base-en-ru"):
        """Инициализирует токенизатор и модель для использования e5-base-en-ru с Hugging Face."""
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def vectorize_text(self, text: str) -> np.ndarray:
        """Векторизует текст и возвращает нормализованный вектор."""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)

        with torch.no_grad():
            embeddings = self.model(**inputs).last_hidden_state

        mean_embedding = embeddings.mean(dim=1)
        normalized_embedding = F.normalize(mean_embedding, p=2, dim=1)

        return normalized_embedding.squeeze().numpy()
