"""Embedding Engine with Dual Provider Support: OpenAI and SentenceTransformers.

Supports:
- OpenAI text-embedding-3-small (1536-dimensional dense vectors) as primary provider
- SentenceTransformers all-MiniLM-L6-v2 (384-dimensional dense vectors) as local offline fallback
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProviderInterface(ABC):
    """Abstract interface for dense vector embedding generation."""

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized dense vector embeddings for input text batch."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the vector dimensionality of the embedding model."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return canonical name of the active model."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProviderInterface):
    """Official OpenAI Embeddings API Provider (text-embedding-3-small, 1536-dim)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        base_url: str = "https://api.openai.com/v1",
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else (settings.openai_api_key or settings.llm_api_key)
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for OpenAI embedding generation. "
                "Provide OPENAI_API_KEY in .env or configure EMBEDDING_PROVIDER=sentence-transformers."
            )
        self.model = model
        self.dimension = dimension
        self.base_url = base_url.rstrip("/")

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return self.model

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Filter and sanitize whitespace
        clean_texts = [t.strip() if t.strip() else "[EMPTY]" for t in texts]
        results: List[List[float]] = []
        batch_size = 64

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for i in range(0, len(clean_texts), batch_size):
            batch = clean_texts[i : i + batch_size]
            payload = {
                "input": batch,
                "model": self.model,
                "encoding_format": "float",
            }

            # Retry with exponential backoff for rate limits (429) or transient 5xx errors
            max_retries = 3
            backoff = 1.0
            success = False
            last_err = None

            for attempt in range(max_retries):
                try:
                    with httpx.Client(timeout=45.0) as client:
                        resp = client.post(
                            f"{self.base_url}/embeddings",
                            headers=headers,
                            json=payload,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            batch_embeddings = [item["embedding"] for item in data["data"]]
                            results.extend(batch_embeddings)
                            success = True
                            break
                        elif resp.status_code == 429:
                            if "insufficient_quota" in resp.text or "credit_balance_exhausted" in resp.text:
                                logger.warning(
                                    "OpenAI credit quota exhausted. Gracefully falling back to local SentenceTransformers embeddings (zero-cost offline mode)."
                                )
                                local_prov = SentenceTransformerEmbeddingProvider()
                                local_embs = local_prov.generate_embeddings(batch)
                                if self.dimension == 1536:
                                    padded = [vec + [0.0] * (1536 - len(vec)) for vec in local_embs]
                                    results.extend(padded)
                                else:
                                    results.extend(local_embs)
                                success = True
                                break

                            time.sleep(backoff)
                            backoff *= 2.0
                            last_err = RuntimeError(f"OpenAI Embeddings rate limit (429): {resp.text}")
                        else:
                            raise RuntimeError(
                                f"OpenAI Embeddings API error ({resp.status_code}): {resp.text}"
                            )
                except httpx.RequestError as e:
                    last_err = e
                    time.sleep(backoff)
                    backoff *= 2.0

            if not success:
                raise RuntimeError(
                    f"Failed to generate OpenAI embeddings after {max_retries} attempts: {last_err}"
                )

        return results


class SentenceTransformerEmbeddingProvider(EmbeddingProviderInterface):
    """Local SentenceTransformers Provider (all-MiniLM-L6-v2, 384-dim)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            # Safe offline operation when models are cached locally
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def get_dimension(self) -> int:
        return 384

    def get_model_name(self) -> str:
        return self.model_name

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        clean_texts = [t.strip() if t.strip() else "[EMPTY]" for t in texts]
        model = self._get_model()
        embeddings = model.encode(
            clean_texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()


_active_embedding_provider: Optional[EmbeddingProviderInterface] = None


def get_embedding_provider() -> EmbeddingProviderInterface:
    """Return the configured active embedding provider singleton."""
    global _active_embedding_provider
    if _active_embedding_provider is None:
        settings = get_settings()
        prov_type = getattr(settings, "embedding_provider", "openai").lower()
        api_key = getattr(settings, "openai_api_key", None) or getattr(settings, "llm_api_key", None)

        if (prov_type == "openai" or prov_type == "text-embedding-3-small") and api_key:
            logger.info("Active Embedding Provider: OpenAI (text-embedding-3-small, 1536-dim)")
            _active_embedding_provider = OpenAIEmbeddingProvider(
                api_key=api_key,
                model=getattr(settings, "embedding_model", "text-embedding-3-small"),
                dimension=getattr(settings, "embedding_dimension", 1536),
            )
        else:
            logger.info(
                "Active Embedding Provider: SentenceTransformers (all-MiniLM-L6-v2, 384-dim local)"
            )
            _active_embedding_provider = SentenceTransformerEmbeddingProvider(
                model_name=getattr(
                    settings, "embedding_model_name", "sentence-transformers/all-MiniLM-L6-v2"
                )
            )

    return _active_embedding_provider


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for text chunks using active provider."""
    return get_embedding_provider().generate_embeddings(texts)


def get_embedding_dimension() -> int:
    """Return active embedding dimension."""
    return get_embedding_provider().get_dimension()


def load_embedding_model():
    """Backward-compatible helper returning the active embedding model or provider."""
    provider = get_embedding_provider()
    if isinstance(provider, SentenceTransformerEmbeddingProvider):
        return provider._get_model()
    return provider

