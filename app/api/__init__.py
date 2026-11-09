"""API application package initialization."""

from fastapi import APIRouter
from app.api.routes import (
    analysis_router,
    documents_router,
    extraction_router,
    health_router,
    search_router,
    workspaces_router,
)

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(workspaces_router)
api_router.include_router(documents_router)
api_router.include_router(search_router)
api_router.include_router(extraction_router)
api_router.include_router(analysis_router)

__all__ = ["api_router"]
