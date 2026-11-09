"""API Route: Semantic Retrieval."""

from fastapi import APIRouter, HTTPException

from app.agents.document_agent import DocumentAgentService
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(tags=["Search & Retrieval"])


@router.post("/search", response_model=SearchResponse)
def semantic_search(request: SearchRequest):
    """Retrieve semantically similar passages with source-page attribution."""
    service = DocumentAgentService()
    try:
        results = service.search(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
            session_id=request.session_id,
            filter_tables_only=request.filter_tables_only,
        )
        return results
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

