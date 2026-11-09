"""Pydantic schemas for Document Chunks and Vector Payloads."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    document_id: str
    filename: str
    page_number: int = Field(..., ge=1)
    page_chunk_index: int = Field(default=1, ge=1)
    section: Optional[str] = None
    is_table: bool = False
    table_headers: Optional[list[str]] = None
    token_count: Optional[int] = None


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    page_chunk_index: int
    text: str
    section: Optional[str] = None
    is_table: bool = False
    metadata: Optional[Dict[str, Any]] = None

