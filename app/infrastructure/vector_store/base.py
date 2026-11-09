"""Abstract Vector Store Interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStoreInterface(ABC):
    """Abstract interface for vector database operations."""

    @abstractmethod
    def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> int:
        """Store chunk vectors and retrievable metadata payloads. Return count of upserted items."""
        pass

    @abstractmethod
    def search_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search with optional metadata filtering."""
        pass

    @abstractmethod
    def count_chunks(self) -> int:
        """Return total count of indexed chunks in the primary collection."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Verify vector database connectivity and collection health."""
        pass

    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chunks belonging to a document. Subclasses can override."""
        return []

