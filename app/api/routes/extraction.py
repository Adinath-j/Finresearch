"""API Route: Financial Metric Extraction."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from app.agents.extraction_agent import ExtractionAgentService

router = APIRouter(tags=["Extraction"])


@router.get("/documents/{document_id}/extraction")
def get_extracted_financials(document_id: str):
    """Retrieve extracted financial metrics, statements, and ratios for a document."""
    service = ExtractionAgentService()
    results = service.get_extracted_financials(document_id)
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No extracted financial metrics found for document {document_id}. Ingest the document first.",
        )
    return results

