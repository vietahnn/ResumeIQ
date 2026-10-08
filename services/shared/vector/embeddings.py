import logging
from typing import List, Optional, Any
from services.shared.config import settings

logger = logging.getLogger("SharedEmbeddings")

_embedding_model: Optional[Any] = None


# Returns a singleton SentenceTransformer embedding model instance
def get_embedding_model() -> Any:
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading shared embedding model: %s", settings.EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model


# Encodes a single text string into a normalized dense vector
def embed_text(text: str) -> List[float]:
    model = get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)


# Encodes a batch of text strings into normalized dense vectors
def embed_batch(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in embeddings]
