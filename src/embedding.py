"""Embedding service using sentence-transformers."""

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from config import EMBEDDING_INSTRUCTION, EMBEDDING_MODEL, MODEL_DIR


class EmbeddingService:
    """Local embedding service with model caching."""

    def __init__(self, model_name: str = EMBEDDING_MODEL, cache_dir: str = str(MODEL_DIR)) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, cache_folder=self.cache_dir)
        return self._model

    def embed(self, text: str) -> List[float]:
        """Embed a single text into a normalized vector."""
        model = self._load_model()
        instruction = EMBEDDING_INSTRUCTION
        vector = model.encode(
            instruction + text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vector.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in a batch."""
        model = self._load_model()
        instruction = EMBEDDING_INSTRUCTION
        vectors = model.encode(
            [instruction + t for t in texts],
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return a singleton embedding service."""
    return EmbeddingService()


def embed_text(text: str) -> List[float]:
    """Convenience function for single text embedding."""
    return get_embedding_service().embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Convenience function for batch text embedding."""
    return get_embedding_service().embed_batch(texts)
