"""Red Flag Agent Service.

Coordinates hybrid financial risk detection combining deterministic metric rules
with LLM narrative disclosure analysis and repository persistence.
"""

import logging
from typing import Any, Dict, List, Optional

from app.agents.red_flag_agent.analyzer import DisclosureAnalyzer
from app.agents.red_flag_agent.rule_engine import RuleEngine
from app.infrastructure.database import DatabaseRepositoryInterface, get_database_repository
from app.infrastructure.vector_store import VectorStoreInterface, get_vector_store
from app.schemas.agents import ExtractedFinancials, RedFlagFinding

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


class RedFlagAgentService:
    """Production service coordinating financial risk detection and evidence grounding."""

    def __init__(
        self,
        repository: Optional[DatabaseRepositoryInterface] = None,
        vector_store: Optional[VectorStoreInterface] = None,
        rule_engine: Optional[RuleEngine] = None,
        analyzer: Optional[DisclosureAnalyzer] = None,
    ):
        self.repo = repository or get_database_repository()
        self.vector_store = vector_store or get_vector_store()
        self.rule_engine = rule_engine or RuleEngine()
        self.analyzer = analyzer or DisclosureAnalyzer()

    def analyze_document_risks(
        self,
        document_id: str,
        financials: ExtractedFinancials,
        session_id: Optional[str] = None,
        chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> List[RedFlagFinding]:
        """Execute hybrid financial risk detection."""
        logger.info("Starting Red Flag risk detection for document: %s", document_id)
        doc = self.repo.get_document_by_id(document_id)
        filename = doc.get("filename", "document.pdf") if doc else "document.pdf"

        # 1. Deterministic Rule-Based Findings
        rule_findings = self.rule_engine.evaluate_financials(financials)
        logger.info("Deterministic rule engine identified %d risk findings", len(rule_findings))

        # 2. Gather narrative chunks for disclosure analysis
        doc_chunks = chunks
        if not doc_chunks:
            if hasattr(self.vector_store, "get_chunks_by_document"):
                doc_chunks = self.vector_store.get_chunks_by_document(document_id)
            if not doc_chunks:
                query_results = self.vector_store.search_chunks(
                    query_embedding=[0.0] * 384,
                    top_k=50,
                    filters={"document_id": document_id},
                )
                doc_chunks = [
                    {
                        "text": r["text"],
                        "page_number": r["metadata"].get("page_number", 1),
                        "is_table": r["metadata"].get("is_table", False),
                        "section": r["metadata"].get("section", ""),
                    }
                    for r in query_results
                ]

        # 3. LLM-Based Disclosure Analysis Findings
        disclosure_findings = self.analyzer.analyze_disclosures(
            document_id=document_id,
            filename=filename,
            chunks=doc_chunks or [],
            fiscal_year=financials.fiscal_year,
        )
        logger.info("LLM disclosure analysis identified %d risk findings", len(disclosure_findings))

        # 4. Merge, rank, and deduplicate
        all_findings = rule_findings + disclosure_findings
        all_findings.sort(
            key=lambda f: SEVERITY_ORDER.get(f.severity.value, 1),
            reverse=True,
        )

        # 5. Persist to repository
        findings_to_store: List[Dict[str, Any]] = []
        for f in all_findings:
            findings_to_store.append({
                "finding_id": f.finding_id,
                "category": f.category.value,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description,
                "detection_method": "RULE_BASED" if f in rule_findings else "LLM_DISCLOSURE",
                "supporting_evidence": f.supporting_evidence,
                "source_page": f.source_citation.page_number,
                "requires_review": True,
            })

        stored_count = self.repo.store_red_flag_findings(
            document_id=document_id,
            findings=findings_to_store,
            session_id=session_id,
        )
        logger.info("Successfully persisted %d red flag findings for document %s", stored_count, document_id)

        # 6. Record agent run in ai_agent_runs
        self.repo.record_agent_run(
            document_id=document_id,
            session_id=session_id,
            agent_name="RED_FLAG_AGENT",
            status="COMPLETED",
            input_payload={"rule_count": len(rule_findings), "disclosure_count": len(disclosure_findings)},
            output_payload={"total_findings": len(all_findings)},
        )

        return all_findings

    def get_document_red_flags(self, document_id: str) -> List[Dict[str, Any]]:
        """Retrieve stored red flag findings from repository."""
        return self.repo.get_red_flag_findings(document_id)

