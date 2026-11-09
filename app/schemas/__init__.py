"""Schema package exports."""

from app.schemas.workspace import (
    WorkspaceBase,
    WorkspaceCreate,
    WorkspaceResponse,
    ResearchSessionBase,
    ResearchSessionCreate,
    ResearchSessionResponse,
)
from app.schemas.document import (
    DocumentSummary,
    DocumentUploadResponse,
    SeedDocumentResult,
)
from app.schemas.chunk import DocumentChunk, ChunkMetadata
from app.schemas.search import SearchRequest, SearchResultItem, SearchResponse
from app.schemas.agents import (
    SourceCitation,
    ExtractedMetric,
    ExtractedFinancials,
    RedFlagFinding,
    ComparisonResult,
    ResearchAnswer,
    FinancialReport,
)

__all__ = [
    "WorkspaceBase",
    "WorkspaceCreate",
    "WorkspaceResponse",
    "ResearchSessionBase",
    "ResearchSessionCreate",
    "ResearchSessionResponse",
    "DocumentSummary",
    "DocumentUploadResponse",
    "SeedDocumentResult",
    "DocumentChunk",
    "ChunkMetadata",
    "SearchRequest",
    "SearchResultItem",
    "SearchResponse",
    "SourceCitation",
    "ExtractedMetric",
    "ExtractedFinancials",
    "RedFlagFinding",
    "ComparisonResult",
    "ResearchAnswer",
    "FinancialReport",
]

