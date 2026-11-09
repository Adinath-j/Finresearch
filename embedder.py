"""Backward-compatible embedder module delegating to app infrastructure."""

from app.infrastructure.document_processing.embedder import (
    generate_embeddings,
    get_embedding_dimension,
    load_embedding_model,
)

__all__ = [
    "load_embedding_model",
    "generate_embeddings",
    "get_embedding_dimension",
]
