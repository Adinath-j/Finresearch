"""Extraction Agent Service.

Coordinates extraction of financial metrics, persistence in ai_financial_metrics,
and audit trail tracking in ai_agent_runs.
"""

import logging
from typing import Any, Dict, List, Optional

from app.agents.extraction_agent.extractor import MetricExtractor
from app.infrastructure.database import DatabaseRepositoryInterface, get_database_repository
from app.infrastructure.vector_store import VectorStoreInterface, get_vector_store
from app.schemas.agents import ExtractedFinancials, ExtractedMetric

logger = logging.getLogger(__name__)


class ExtractionAgentService:
    """Production service coordinating structured financial information extraction."""

    def __init__(
        self,
        repository: Optional[DatabaseRepositoryInterface] = None,
        vector_store: Optional[VectorStoreInterface] = None,
        extractor: Optional[MetricExtractor] = None,
    ):
        self.repo = repository or get_database_repository()
        self.vector_store = vector_store or get_vector_store()
        self.extractor = extractor or MetricExtractor()

    def extract_document_financials(
        self,
        document_id: str,
        session_id: Optional[str] = None,
        chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> ExtractedFinancials:
        """Execute full financial extraction pipeline for a document."""
        logger.info("Starting financial extraction for document: %s", document_id)
        doc = self.repo.get_document_by_id(document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found in database.")

        filename = doc.get("filename", "document.pdf")
        company_name = doc.get("metadata", {}).get("company_name")

        # 1. Gather document chunks (from argument or vector store query)
        doc_chunks = chunks
        if not doc_chunks:
            if hasattr(self.vector_store, "get_chunks_by_document"):
                doc_chunks = self.vector_store.get_chunks_by_document(document_id)
            if not doc_chunks:
                # Query vector store for chunks belonging to this document
                query_results = self.vector_store.search_chunks(
                    query_embedding=[0.0] * 384,  # Filter primarily by document_id
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

        # 2. Execute extraction
        financials = self.extractor.extract_from_chunks(
            document_id=document_id,
            filename=filename,
            chunks=doc_chunks or [],
            company_name=company_name,
        )

        # 3. Persist extracted metrics to repository
        metrics_to_store: List[Dict[str, Any]] = []
        all_metrics: Dict[str, ExtractedMetric] = {}
        all_metrics.update(financials.income_statement)
        all_metrics.update(financials.balance_sheet)
        all_metrics.update(financials.cash_flow)
        all_metrics.update(financials.ratios)

        for name, m in all_metrics.items():
            metrics_to_store.append({
                "metric_name": m.name,
                "source_label": m.raw_text,
                "numeric_value": str(m.value),
                "currency": m.currency,
                "unit": m.unit,
                "period_type": m.period.value,
                "fiscal_year": m.fiscal_year,
                "statement_type": "KEY_RATIOS" if m.is_calculated else ("INCOME_STATEMENT" if name in financials.income_statement else "BALANCE_SHEET"),
                "is_calculated": m.is_calculated,
                "formula": m.formula,
                "is_consolidated": m.is_consolidated,
                "citation": {
                    "document_id": m.citation.document_id,
                    "page_number": m.citation.page_number,
                    "exact_quote": m.citation.exact_quote,
                    "table_index": m.citation.table_index,
                },
            })

        stored_count = self.repo.store_financial_metrics(document_id, metrics_to_store)
        logger.info("Successfully persisted %d financial metrics for document %s", stored_count, document_id)

        # 4. Record agent run in ai_agent_runs
        self.repo.record_agent_run(
            document_id=document_id,
            session_id=session_id,
            agent_name="EXTRACTION_AGENT",
            status="COMPLETED",
            input_payload={"chunks_count": len(doc_chunks or [])},
            output_payload={"metrics_extracted": len(all_metrics)},
        )

        return financials

    def get_extracted_financials(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored financial metrics for document."""
        metrics = self.repo.get_financial_metrics(document_id)
        if not metrics:
            return None

        doc = self.repo.get_document_by_id(document_id)
        return {
            "document_id": document_id,
            "filename": doc.get("filename") if doc else "",
            "total_metrics": len(metrics),
            "metrics": {m["metric_name"]: m for m in metrics},
        }

