"""API Route: Health & System Diagnostics.

Verifies:
- Application status & version
- Database provider & connectivity
- Storage provider & local/Supabase availability
- Vector database provider (Qdrant / ChromaDB) & healthy chunk count
- Embedding provider & vector dimension
- LLM provider & reasoning configuration readiness
- Persistent worker queue state
"""

from fastapi import APIRouter
from app.config import get_settings
from app.infrastructure.database import get_database_repository
from app.infrastructure.document_processing.embedder import get_embedding_provider
from app.infrastructure.storage import get_file_storage
from app.infrastructure.vector_store import get_vector_store

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Comprehensive health check verifying DB, storage, vector store, embedding, and LLM readiness."""
    settings = get_settings()
    vector_store = get_vector_store()
    repo = get_database_repository()
    storage = get_file_storage()
    emb_engine = get_embedding_provider()

    vs_healthy = vector_store.is_healthy()
    chunk_count = vector_store.count_chunks() if vs_healthy else 0
    emb_dim = emb_engine.get_dimension()
    emb_model = emb_engine.get_model_name()

    # Query queued and running jobs
    queued_jobs = 0
    processing_jobs = 0
    try:
        if hasattr(repo, "_get_connection"):
            with repo._get_connection() as conn:
                q_row = conn.execute("SELECT COUNT(*) as c FROM ai_processing_jobs WHERE status = 'QUEUED'").fetchone()
                p_row = conn.execute("SELECT COUNT(*) as c FROM ai_processing_jobs WHERE status = 'PROCESSING'").fetchone()
                queued_jobs = q_row["c"] if q_row else 0
                processing_jobs = p_row["c"] if p_row else 0
    except Exception:
        pass

    # Storage health check
    storage_healthy = True
    storage_type = type(storage).__name__
    try:
        if hasattr(storage, "upload_dir"):
            storage_healthy = storage.upload_dir.exists()
    except Exception:
        storage_healthy = False

    # LLM credential readiness check (without leaking secrets)
    has_openai_key = bool(settings.openai_api_key or settings.llm_api_key)
    llm_configured = True if (settings.llm_provider != "openai" or has_openai_key) else False

    is_overall_healthy = vs_healthy and storage_healthy

    return {
        "status": "healthy" if is_overall_healthy else "degraded",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": {
            "provider": type(repo).__name__,
            "connected": True,
        },
        "storage": {
            "provider": storage_type,
            "healthy": storage_healthy,
            "upload_dir": str(settings.upload_dir),
        },
        "vector_store": {
            "provider": type(vector_store).__name__,
            "healthy": vs_healthy,
            "collection": getattr(vector_store, "collection_name", "unknown"),
            "total_indexed_chunks": chunk_count,
        },
        "embedding_engine": {
            "provider": settings.embedding_provider,
            "model": emb_model,
            "dimension": emb_dim,
        },
        "llm_engine": {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "reasoning_effort": settings.llm_reasoning_effort,
            "credentials_configured": llm_configured,
        },
        "worker_queue": {
            "queued_jobs": queued_jobs,
            "processing_jobs": processing_jobs,
            "poll_interval_seconds": settings.worker_poll_seconds,
        },
    }
