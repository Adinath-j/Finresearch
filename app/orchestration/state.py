"""Shared Typed State for LangGraph Multi-Agent Orchestration."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentExecutionLog(BaseModel):
    step_name: str
    agent: str
    status: str
    timestamp: str
    duration_ms: Optional[int] = None
    message: Optional[str] = None


class FinancialResearchState(BaseModel):
    """Shared state object routed across all LangGraph nodes."""

    # Context & Identifiers
    workspace_id: Optional[str] = "default-workspace"
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    document_id: str
    filename: str
    file_bytes: Optional[bytes] = None
    storage_path: Optional[str] = None

    # Execution Tracking
    job_id: Optional[str] = None
    current_phase: str = "INITIALIZED"
    is_failed: bool = False
    validation_passed: bool = False
    retry_count: int = 0
    errors: List[str] = Field(default_factory=list)
    execution_steps: List[AgentExecutionLog] = Field(default_factory=list)

    # Document Agent Stage
    total_pages: int = 0
    total_characters: int = 0
    chunk_count: int = 0
    is_indexed: bool = False
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)

    # Extraction Agent Stage (Milestone 2)
    extracted_financials: Optional[Dict[str, Any]] = None
    extracted_metrics_count: int = 0

    # Red Flag Agent Stage (Milestone 2)
    red_flag_findings: List[Dict[str, Any]] = Field(default_factory=list)
    red_flag_count: int = 0

    # Output Summary
    final_summary: Optional[Dict[str, Any]] = None
