"""Pydantic schemas for Document Uploads, Metadata, and Retrieval."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    document_id: str
    workspace_id: Optional[str] = None
    filename: str
    stored_filename: str
    sha256: str
    total_pages: int
    total_characters: int
    chunk_count: int
    indexed: bool
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    total_pages: int
    characters_extracted: int
    text_preview: str
    stored: bool
    indexed: bool
    already_exists: bool
    chunk_count: int
    chunk_preview: List[Dict[str, Any]] = Field(default_factory=list)
    message: str
    session_id: Optional[str] = None
    job_id: Optional[str] = None


class SeedDocumentResult(BaseModel):
    filename: str
    document_id: str
    status: str
    pages: int
    chunks: int

