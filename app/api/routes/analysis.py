"""API Routes: Risk Analysis, Workflow Orchestration & Job Status."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.agents.red_flag_agent import RedFlagAgentService
from app.infrastructure.database import get_database_repository
from app.orchestration.workflow import MultiAgentWorkflowOrchestrator

router = APIRouter(tags=["Analysis & Orchestration"])


class ProcessDocumentRequest(BaseModel):
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Document file name")
    workspace_id: Optional[str] = Field(default="default-workspace")
    session_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    storage_path: Optional[str] = Field(default=None, description="Filesystem or storage bucket path")


@router.post("/documents/process")
@router.post("/documents/{document_id}/process")
def process_document(
    request: Optional[ProcessDocumentRequest] = None,
    document_id: Optional[str] = None,
):
    """Trigger the multi-agent analysis workflow (Document -> Extraction -> Red Flag)."""
    try:
        doc_id = document_id or (request.document_id if request else None)
        if not doc_id:
            raise HTTPException(status_code=400, detail="Document ID is required.")

        repo = get_database_repository()
        doc = repo.get_document_by_id(doc_id)
        filename = (request.filename if request else None) or (doc.get("filename") if doc else "document.pdf")
        workspace_id = (request.workspace_id if request else None) or (doc.get("workspace_id") if doc else "default-workspace")
        session_id = (request.session_id if request else None) or (doc.get("session_id") if doc else None)
        storage_path = (request.storage_path if request else None) or (doc.get("storage_path") if doc else None)

        final_state = MultiAgentWorkflowOrchestrator.run_pipeline(
            document_id=doc_id,
            filename=filename,
            storage_path=storage_path,
            workspace_id=workspace_id,
            session_id=session_id,
        )

        return {
            "job_id": final_state.job_id,
            "document_id": final_state.document_id,
            "status": "COMPLETED" if not final_state.is_failed else "FAILED",
            "phase": final_state.current_phase,
            "pages": final_state.total_pages,
            "chunks": final_state.chunk_count,
            "metrics_extracted": final_state.extracted_metrics_count,
            "red_flags": final_state.red_flag_count,
            "errors": final_state.errors,
            "execution_steps": [s.model_dump() for s in final_state.execution_steps],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/documents/{document_id}/status")
def get_document_status(document_id: str):
    """Query ingestion and processing status for an AI document."""
    repo = get_database_repository()
    doc = repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    runs = repo.get_agent_runs(document_id)
    stages = {r["agent_name"]: r["status"] for r in runs}

    return {
        "document_id": document_id,
        "filename": doc.get("filename"),
        "total_pages": doc.get("total_pages", 0),
        "total_characters": doc.get("total_characters", 0),
        "chunk_count": doc.get("chunk_count", 0),
        "indexed": bool(doc.get("indexed", 0)),
        "created_at": doc.get("created_at"),
        "stages": stages or {"DOCUMENT_AGENT": "INDEXED" if doc.get("indexed") else "PENDING"},
    }


@router.get("/documents/{document_id}/red-flags")
def get_document_red_flags(document_id: str):
    """Retrieve red flag risk findings and warnings for a document."""
    service = RedFlagAgentService()
    findings = service.get_document_red_flags(document_id)
    return {
        "document_id": document_id,
        "total_findings": len(findings),
        "findings": findings,
    }


@router.get("/workflows/{run_id}/status")
def get_workflow_run_status(run_id: str):
    """Query execution status of an agent run or processing job."""
    repo = get_database_repository()
    job = repo.get_processing_job(run_id)
    if job:
        return job

    raise HTTPException(status_code=404, detail=f"Workflow run or job {run_id} not found.")

