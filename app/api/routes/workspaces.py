"""API Routes: Workspaces and Research Sessions Management."""

from typing import List
from fastapi import APIRouter, HTTPException

from app.infrastructure.database import get_database_repository
from app.schemas.workspace import (
    ResearchSessionCreate,
    ResearchSessionResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)

router = APIRouter(tags=["Workspaces & Sessions"])


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
def create_workspace(payload: WorkspaceCreate):
    """Create a new research workspace container."""
    repo = get_database_repository()
    created = repo.create_workspace(name=payload.name, description=payload.description)
    return WorkspaceResponse(**created)


@router.get("/workspaces", response_model=List[WorkspaceResponse])
def list_workspaces():
    """List all available research workspaces."""
    repo = get_database_repository()
    workspaces = repo.list_workspaces()
    return [WorkspaceResponse(**w) for w in workspaces]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: str):
    """Get workspace details by ID."""
    repo = get_database_repository()
    ws = repo.get_workspace(workspace_id)
    if not ws:
        if workspace_id == "default-workspace":
            ws = repo.create_workspace(
                name="Default Workspace",
                description="Default institutional research workspace",
                workspace_id="default-workspace",
            )
            return WorkspaceResponse(**ws)
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found.")
    return WorkspaceResponse(**ws)


@router.post("/workspaces/{workspace_id}/sessions", response_model=ResearchSessionResponse, status_code=201)
def create_session(workspace_id: str, payload: ResearchSessionCreate):
    """Create a new research session inside a workspace."""
    repo = get_database_repository()
    ws = repo.get_workspace(workspace_id)
    if not ws:
        if workspace_id == "default-workspace":
            ws = repo.create_workspace(
                name="Default Workspace",
                description="Default institutional research workspace",
                workspace_id="default-workspace",
            )
        else:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found.")

    session = repo.create_session(
        workspace_id=workspace_id,
        title=payload.title,
        description=payload.description,
    )
    return ResearchSessionResponse(**session)


@router.get("/workspaces/{workspace_id}/sessions", response_model=List[ResearchSessionResponse])
def list_workspace_sessions(workspace_id: str):
    """List all research sessions within a workspace."""
    repo = get_database_repository()
    ws = repo.get_workspace(workspace_id)
    if not ws:
        if workspace_id == "default-workspace":
            ws = repo.create_workspace(
                name="Default Workspace",
                description="Default institutional research workspace",
                workspace_id="default-workspace",
            )
        else:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found.")

    sessions = repo.list_sessions(workspace_id=workspace_id)
    return [ResearchSessionResponse(**s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ResearchSessionResponse)
def get_session(session_id: str):
    """Get research session details by ID, including assigned document IDs."""
    repo = get_database_repository()
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")
    return ResearchSessionResponse(**session)

