"""Factory for instantiating the active VectorStore."""

import logging
from typing import Optional

from app.config import get_settings
from app.infrastructure.vector_store.base import VectorStoreInterface
from app.infrastructure.vector_store.chroma import ChromaVectorStore
from app.infrastructure.vector_store.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

_vector_store_instance: Optional[VectorStoreInterface] = None


class VectorStoreFactory:
    """Manages vector store lifecycle and fallback strategy."""

    @staticmethod
    def create() -> VectorStoreInterface:
        settings = get_settings()
        v_type = settings.vector_store_type.lower()

        if v_type == "qdrant":
            logger.info("Initializing explicit Qdrant vector store at %s", settings.qdrant_url)
            return QdrantVectorStore()

        if v_type == "chroma":
            logger.info("Initializing ChromaDB vector store at %s", settings.chroma_db_dir)
            return ChromaVectorStore()

        # 'auto' mode: Probe Qdrant; if reachable use Qdrant, otherwise fallback to ChromaDB
        try:
            qdrant = QdrantVectorStore()
            if qdrant.is_healthy():
                logger.info("Qdrant endpoint responsive. Using QdrantVectorStore.")
                return qdrant
            else:
                logger.info("Qdrant not reachable at %s. Falling back to persistent ChromaDB.", settings.qdrant_url)
                return ChromaVectorStore()
        except Exception as e:
            logger.info("Error connecting to Qdrant (%s). Falling back to persistent ChromaDB.", e)
            return ChromaVectorStore()


def get_vector_store() -> VectorStoreInterface:
    """Singleton getter for active vector store."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreFactory.create()
    return _vector_store_instance

