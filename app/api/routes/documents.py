"""API Routes: Document Upload, Registration, and Management."""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.agents.document_agent import DocumentAgentService
from app.infrastructure.database import get_database_repository
from app.infrastructure.storage import get_file_storage
from app.schemas.document import DocumentSummary, DocumentUploadResponse, SeedDocumentResult

router = APIRouter(tags=["Documents"])


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Query(default=None, description="Optional target workspace ID"),
    session_id: Optional[str] = Query(default=None, description="Optional target session ID"),
):
    """Upload, deduplicate, parse, chunk, embed, index a financial PDF, and queue an analysis job."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    try:
        content = await file.read()
        service = DocumentAgentService()
        result = service.process_pdf_upload(
            file_bytes=content,
            filename=file.filename,
            workspace_id=workspace_id,
            session_id=session_id,
        )

        # Create durable background processing job for downstream Extraction & Red Flag agents
        repo = get_database_repository()
        job = repo.create_processing_job(
            document_id=result.document_id,
            workspace_id=workspace_id or "default-workspace",
            session_id=session_id,
            status="QUEUED",
            current_stage="DOCUMENT_INGESTED",
        )
        result.job_id = job["job_id"]

        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except RuntimeError as re:
        raise HTTPException(status_code=502, detail=f"Storage failure: {re}") from re
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await file.close()


@router.post("/sessions/{session_id}/documents/upload", response_model=DocumentUploadResponse)
async def upload_document_to_session(
    session_id: str,
    file: UploadFile = File(...),
):
    """Upload and attach a financial PDF directly to a research session."""
    repo = get_database_repository()
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    return await upload_document(
        file=file,
        workspace_id=session["workspace_id"],
        session_id=session_id,
    )


@router.get("/documents/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str):
    """Fetch status and metadata for an ingested document."""
    service = DocumentAgentService()
    summary = service.get_document_summary(document_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return summary


@router.get("/documents", response_model=List[DocumentSummary])
def list_documents(workspace_id: Optional[str] = Query(default=None)):
    """List all registered documents in the system or filtered by workspace."""
    repo = get_database_repository()
    raw_docs = repo.list_documents(workspace_id=workspace_id)
    summaries = []
    for d in raw_docs:
        summaries.append(
            DocumentSummary(
                document_id=d["document_id"],
                workspace_id=d.get("workspace_id"),
                filename=d["filename"],
                stored_filename=d["stored_filename"],
                sha256=d["sha256"],
                total_pages=d.get("total_pages", 0),
                total_characters=d.get("total_characters", 0),
                chunk_count=d.get("chunk_count", 0),
                indexed=bool(d.get("indexed", 0)),
                created_at=d["created_at"],
                metadata=d.get("metadata", {}),
            )
        )
    return summaries


@router.post("/documents/seed", response_model=List[SeedDocumentResult])
def ingest_seed_documents():
    """Trigger ingestion of preloaded seed company documents."""
    service = DocumentAgentService()
    results = service.ingest_seed_documents()
    return results


@router.get("/documents/{document_id}/file")
def download_document_file(document_id: str):
    """Download or stream the stored original PDF file using the stored object key."""
    from fastapi import Response

    storage = get_file_storage()
    repo = get_database_repository()
    doc = repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found in database.")

    meta = doc.get("metadata") or {}
    object_key = meta.get("object_key") or doc.get("stored_filename") or f"{document_id}.pdf"

    try:
        file_bytes = storage.get_file_bytes(document_id, object_key=object_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Physical file for document {document_id} not found in storage.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document from storage: {exc}")

    filename = doc.get("filename", f"{document_id}.pdf")
    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Safely delete document metadata, file storage, and associated records."""
    storage = get_file_storage()
    repo = get_database_repository()
    doc = repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    storage.delete_file(document_id)
    # Delete from ai_documents and legacy documents
    if hasattr(repo, "_get_connection"):
        with repo._get_connection() as conn:
            conn.execute("DELETE FROM ai_documents WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))

    return {"status": "deleted", "document_id": document_id}

