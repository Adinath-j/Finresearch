"""API routes exports."""

from app.api.routes.analysis import router as analysis_router
from app.api.routes.documents import router as documents_router
from app.api.routes.extraction import router as extraction_router
from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router
from app.api.routes.workspaces import router as workspaces_router

__all__ = [
    "health_router",
    "workspaces_router",
    "documents_router",
    "search_router",
    "extraction_router",
    "analysis_router",
]
