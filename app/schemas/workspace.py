"""Pydantic schemas for Workspaces and Research Sessions."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Workspace display name")
    description: Optional[str] = Field(default=None, description="Optional workspace description")


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceResponse(WorkspaceBase):
    workspace_id: str
    created_at: str
    updated_at: str
    session_count: int = 0
    document_count: int = 0


class ResearchSessionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Session title")
    description: Optional[str] = Field(default=None, description="Detailed session description")


class ResearchSessionCreate(ResearchSessionBase):
    pass


class ResearchSessionResponse(ResearchSessionBase):
    session_id: str
    workspace_id: str
    status: str = "ACTIVE"
    created_at: str
    updated_at: str
    document_ids: List[str] = Field(default_factory=list)

