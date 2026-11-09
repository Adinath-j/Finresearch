"""Multi-Agent Financial Research System - FastAPI Application Entry Point.

Infosys Springboard — Vidzai Digital
Milestone 1 Implementation
"""

import logging
import os
from contextlib import asynccontextmanager

# Ensure offline operation so cached model is used without network timeouts
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.infrastructure.database import get_database_repository
from app.infrastructure.storage import get_file_storage
from app.infrastructure.vector_store import get_vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("document-agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    settings = get_settings()
    logger.info("Starting %s v%s in %s mode...", settings.app_name, settings.app_version, settings.app_env)

    # Initialize singletons
    get_database_repository()
    get_file_storage()
    vs = get_vector_store()
    logger.info("Active vector store provider: %s", type(vs).__name__)

    yield

    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title="Multi-Agent Financial Research System",
    description="Enterprise-grade financial document ingestion, parsing, vector retrieval, and research management.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Service status and identification endpoint."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "documentation": "/docs",
    }


# Include all modular API routers
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=settings.debug)
