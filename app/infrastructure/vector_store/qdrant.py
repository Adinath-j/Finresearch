"""Qdrant Vector Database Integration via REST API."""

import logging
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings
from app.infrastructure.vector_store.base import VectorStoreInterface

logger = logging.getLogger(__name__)


def _to_point_id(chunk_id: str) -> str:
    """Ensure point ID is a valid UUID string for Qdrant compatibility."""
    try:
        # Check if already a valid UUID
        return str(uuid.UUID(chunk_id))
    except (ValueError, AttributeError):
        # Generate deterministic UUIDv5 from chunk_id string
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(chunk_id)))


class QdrantVectorStore(VectorStoreInterface):
    """Production vector database interface connecting to Qdrant via HTTP REST API."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
    ):
        settings = get_settings()
        self.url = (url or settings.qdrant_url).rstrip("/")
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name or settings.qdrant_collection
        self.vector_size = vector_size or settings.embedding_dimension

        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["api-key"] = self.api_key

        self._ensure_collection()

    def _ensure_collection(self) -> bool:
        """Create Qdrant collection with Cosine distance if it does not already exist."""
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"{self.url}/collections/{self.collection_name}", headers=self.headers)
                if res.status_code == 200:
                    return True

                # Create collection
                payload = {
                    "vectors": {
                        "size": self.vector_size,
                        "distance": "Cosine",
                    }
                }
                put_res = client.put(
                    f"{self.url}/collections/{self.collection_name}",
                    headers=self.headers,
                    json=payload,
                )
                if put_res.status_code in (200, 201):
                    logger.info("Created Qdrant collection: %s", self.collection_name)
                    return True
                logger.warning("Failed to create Qdrant collection: %s %s", put_res.status_code, put_res.text)
                return False
        except Exception as e:
            logger.debug("Could not reach Qdrant server at %s: %s", self.url, e)
            return False

    def is_healthy(self) -> bool:
        """Check if Qdrant endpoint is reachable and responsive."""
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"{self.url}/healthz", headers=self.headers)
                return res.status_code == 200
        except Exception:
            return False

    def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must correspond to exactly one embedding vector.")
        if not chunks:
            return 0

        points = []
        for chunk, emb in zip(chunks, embeddings):
            p_id = _to_point_id(str(chunk["chunk_id"]))
            points.append({
                "id": p_id,
                "vector": emb,
                "payload": {
                    "chunk_id": str(chunk["chunk_id"]),
                    "document_id": str(chunk["document_id"]),
                    "filename": str(chunk.get("filename", "")),
                    "page_number": int(chunk.get("page_number", 1)),
                    "page_chunk_index": int(chunk.get("page_chunk_index", 1)),
                    "section": chunk.get("section") or "",
                    "is_table": bool(chunk.get("is_table", False)),
                    "text": chunk.get("text", ""),
                },
            })

        batch_size = 250
        with httpx.Client(timeout=30.0) as client:
            for start in range(0, len(points), batch_size):
                batch = points[start : start + batch_size]
                res = client.put(
                    f"{self.url}/collections/{self.collection_name}/points?wait=true",
                    headers=self.headers,
                    json={"points": batch},
                )
                if res.status_code not in (200, 201):
                    raise RuntimeError(f"Qdrant upsert failed ({res.status_code}): {res.text}")

        return len(points)

    def search_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        query_payload: Dict[str, Any] = {
            "vector": query_embedding,
            "limit": top_k,
            "with_payload": True,
        }

        # Construct Qdrant filter condition if provided
        if filters:
            must_clauses = []
            if "document_id" in filters and filters["document_id"]:
                must_clauses.append({
                    "key": "document_id",
                    "match": {"value": str(filters["document_id"])},
                })
            if "is_table" in filters and filters["is_table"] is not None:
                must_clauses.append({
                    "key": "is_table",
                    "match": {"value": bool(filters["is_table"])},
                })
            if must_clauses:
                query_payload["filter"] = {"must": must_clauses}

        with httpx.Client(timeout=10.0) as client:
            res = client.post(
                f"{self.url}/collections/{self.collection_name}/points/search",
                headers=self.headers,
                json=query_payload,
            )
            if res.status_code != 200:
                raise RuntimeError(f"Qdrant search error ({res.status_code}): {res.text}")

            hits = res.json().get("result", [])
            matches = []
            for hit in hits:
                payload = hit.get("payload", {})
                score = hit.get("score", 0.0)
                # Convert cosine similarity score to distance metric (1.0 - score)
                distance = round(1.0 - score, 4)
                matches.append({
                    "chunk_id": payload.get("chunk_id", str(hit.get("id"))),
                    "text": payload.get("text", ""),
                    "metadata": {
                        "document_id": payload.get("document_id"),
                        "filename": payload.get("filename"),
                        "page_number": payload.get("page_number"),
                        "page_chunk_index": payload.get("page_chunk_index"),
                        "section": payload.get("section"),
                        "is_table": payload.get("is_table"),
                    },
                    "distance": distance,
                    "score": score,
                })
            return matches

    def count_chunks(self) -> int:
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(
                    f"{self.url}/collections/{self.collection_name}/points/count",
                    headers=self.headers,
                    json={"exact": True},
                )
                if res.status_code == 200:
                    return res.json().get("result", {}).get("count", 0)
        except Exception:
            pass
        return 0
