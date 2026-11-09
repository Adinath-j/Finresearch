"""Backward-compatible vector store module delegating to app infrastructure."""

from pathlib import Path
from typing import Any, Dict, List

from app.infrastructure.document_processing.embedder import generate_embeddings
from app.infrastructure.vector_store.chroma import ChromaVectorStore

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "financial_chunks"
TEST_COLLECTION_NAME = "test_financial_chunks"


def get_collection(collection_name: str = COLLECTION_NAME):
    store = ChromaVectorStore(persist_dir=str(CHROMA_DIR), collection_name=collection_name)
    return store.collection


def upsert_chunks(
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    collection_name: str = COLLECTION_NAME,
) -> int:
    store = ChromaVectorStore(persist_dir=str(CHROMA_DIR), collection_name=collection_name)
    return store.upsert_chunks(chunks, embeddings)


def search_chunks(
    query: str,
    top_k: int = 5,
    collection_name: str = COLLECTION_NAME,
) -> List[Dict[str, Any]]:
    if not query.strip():
        raise ValueError("Query must not be empty.")
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    store = ChromaVectorStore(persist_dir=str(CHROMA_DIR), collection_name=collection_name)
    query_emb = generate_embeddings([query])[0]
    return store.search_chunks(query_emb, top_k=top_k)


def count_chunks(collection_name: str = COLLECTION_NAME) -> int:
    store = ChromaVectorStore(persist_dir=str(CHROMA_DIR), collection_name=collection_name)
    return store.count_chunks()
