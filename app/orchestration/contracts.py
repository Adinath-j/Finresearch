"""Orchestration workflows, graph definitions, and node contracts for future milestones."""

from typing import Dict, List
from app.orchestration.state import FinancialResearchState


class WorkflowBlueprint:
    """Defines the four core multi-agent orchestration flows for Milestone 2 and Milestone 3."""

    DOCUMENT_ANALYSIS_FLOW: List[str] = [
        "document_ingestion_node",
        "financial_extraction_node",
        "evidence_validation_node",
        "red_flag_detection_node",
        "persistence_node",
    ]

    RESEARCH_FLOW: List[str] = [
        "query_decomposition_node",
        "hybrid_retrieval_node",
        "evidence_ranking_node",
        "research_synthesis_node",
        "citation_verification_node",
    ]

    COMPARISON_FLOW: List[str] = [
        "entity_resolution_node",
        "financial_metric_normalization_node",
        "variance_calculation_node",
        "comparative_insights_node",
    ]

    REPORT_FLOW: List[str] = [
        "assemble_findings_node",
        "executive_summary_node",
        "risk_synthesis_node",
        "outlook_generation_node",
        "report_structure_compilation_node",
    ]


def should_continue_after_validation(state: FinancialResearchState) -> str:
    """Conditional edge routing: If extraction validation fails, route to retry or error."""
    if state.validation_passed:
        return "red_flag_detection_node"
    return "extraction_correction_node"

