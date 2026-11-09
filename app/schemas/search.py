"""Pydantic schemas for Semantic Retrieval."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of relevant chunks to retrieve")
    document_id: Optional[str] = Field(default=None, description="Optional filter by specific document ID")
    session_id: Optional[str] = Field(default=None, description="Optional filter by research session ID")
    filter_tables_only: Optional[bool] = Field(default=False, description="Filter for tabular chunks only")


class SearchResultItem(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    distance: float
    score: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    result_count: int
    results: List[SearchResultItem]
    retriever_used: str = "qdrant"

