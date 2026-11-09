"""Financial Statement Metric Extractor.

Extracts standardized metrics across Income Statement, Balance Sheet, and Cash Flow
from parsed document tables and narrative disclosures with strict SourceCitation binding.
"""

import json
import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.agents.extraction_agent.calculations import FinancialCalculations
from app.agents.extraction_agent.normalizer import CANONICAL_METRIC_MAP, FinancialNormalizer
from app.infrastructure.llm import LLMProviderInterface, get_llm_provider
from app.schemas.agents import (
    ExtractedFinancials,
    ExtractedMetric,
    FinancialStatementType,
    ReportingPeriod,
    SourceCitation,
)

logger = logging.getLogger(__name__)


class MetricExtractor:
    """Extracts structured financial metrics using hybrid table parsing and LLM assistance."""

    def __init__(self, llm_provider: Optional[LLMProviderInterface] = None):
        self.llm = llm_provider or get_llm_provider()

    def extract_from_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: List[Dict[str, Any]],
        company_name: Optional[str] = None,
    ) -> ExtractedFinancials:
        """Extract financial metrics from parsed chunks, compute ratios, and attach citations."""
        logger.info("Initiating metric extraction for document %s (%d chunks)...", document_id, len(chunks))

        # 1. Identify document-level metadata
        all_text = " ".join([c.get("text", "") for c in chunks[:10]])
        detected_currency = FinancialNormalizer.detect_currency(all_text)
        detected_unit = FinancialNormalizer.detect_unit(all_text)
        detected_scope = FinancialNormalizer.detect_reporting_scope(all_text)
        detected_fy = FinancialNormalizer.detect_fiscal_year(all_text)
        detected_company = company_name or self._infer_company_name(chunks, filename)

        extracted_metrics: Dict[str, ExtractedMetric] = {}

        # 2. Stage 1: Table-based rule extraction
        table_chunks = [c for c in chunks if c.get("is_table", False)]
        for chunk in table_chunks:
            table_metrics = self._parse_table_chunk(
                chunk=chunk,
                document_id=document_id,
                filename=filename,
                currency=detected_currency,
                unit=detected_unit,
                fiscal_year=detected_fy,
                is_consolidated=detected_scope,
            )
            for m in table_metrics:
                # Store if not already extracted or if from a more specific page
                if m.name not in extracted_metrics:
                    extracted_metrics[m.name] = m

        # 2b. Stage 1b: Text line-based heuristic extraction across all chunks
        for chunk in chunks:
            text_metrics = self._parse_text_chunk(
                chunk=chunk,
                document_id=document_id,
                filename=filename,
                currency=detected_currency,
                unit=detected_unit,
                fiscal_year=detected_fy,
                is_consolidated=detected_scope,
            )
            for m in text_metrics:
                if m.name not in extracted_metrics:
                    extracted_metrics[m.name] = m

        # 3. Stage 2: Narrative chunk extraction & LLM fallback if core metrics are missing
        core_metrics_needed = ["REVENUE", "NET_INCOME", "TOTAL_ASSETS", "TOTAL_DEBT"]
        missing_cores = [m for m in core_metrics_needed if m not in extracted_metrics]

        if missing_cores:
            logger.info("Missing core metrics %s. Triggering LLM extraction assistance...", missing_cores)
            llm_metrics = self._extract_with_llm(
                chunks=chunks,
                document_id=document_id,
                filename=filename,
                currency=detected_currency,
                unit=detected_unit,
                fiscal_year=detected_fy,
                is_consolidated=detected_scope,
            )
            for m in llm_metrics:
                if m.name not in extracted_metrics:
                    extracted_metrics[m.name] = m

        # 4. Stage 3: Deterministic Financial Ratio Calculations
        decimal_map: Dict[str, Decimal] = {
            m.name: m.value for m in extracted_metrics.values() if not m.is_calculated
        }
        computed_ratios = FinancialCalculations.compute_all_ratios(decimal_map)

        for ratio_name, (ratio_val, formula) in computed_ratios.items():
            if ratio_name not in extracted_metrics:
                # Cite the primary Income Statement or Balance Sheet source page
                ref_metric = extracted_metrics.get("REVENUE") or extracted_metrics.get("NET_INCOME") or list(extracted_metrics.values())[0] if extracted_metrics else None
                source_page = ref_metric.citation.page_number if ref_metric else 1

                extracted_metrics[ratio_name] = ExtractedMetric(
                    name=ratio_name,
                    value=ratio_val,
                    raw_text=str(ratio_val),
                    currency="PERCENT" if "MARGIN" in ratio_name or "EQUITY" in ratio_name else "RATIO",
                    unit="RATIO",
                    fiscal_year=detected_fy,
                    period=ReportingPeriod.ANNUAL,
                    is_consolidated=detected_scope,
                    citation=SourceCitation(
                        document_id=document_id,
                        filename=filename,
                        page_number=source_page,
                        exact_quote=f"Calculated deterministically: {formula}",
                        is_calculated=True,
                        calculation_basis=formula,
                    ),
                    is_calculated=True,
                    formula=formula,
                )

        # 5. Classify metrics into statements
        income_stmt: Dict[str, ExtractedMetric] = {}
        balance_sheet: Dict[str, ExtractedMetric] = {}
        cash_flow: Dict[str, ExtractedMetric] = {}
        ratios: Dict[str, ExtractedMetric] = {}

        for name, m in extracted_metrics.items():
            if m.is_calculated or "RATIO" in name or "MARGIN" in name:
                ratios[name] = m
            elif name in ("REVENUE", "COGS", "GROSS_PROFIT", "OPERATING_EXPENSES", "OPERATING_INCOME", "EBITDA", "PROFIT_BEFORE_TAX", "NET_INCOME", "EPS_DILUTED"):
                income_stmt[name] = m
            elif name in ("TOTAL_ASSETS", "CURRENT_ASSETS", "NON_CURRENT_ASSETS", "TOTAL_LIABILITIES", "CURRENT_LIABILITIES", "NON_CURRENT_LIABILITIES", "TOTAL_DEBT", "SHAREHOLDERS_EQUITY"):
                balance_sheet[name] = m
            elif name in ("OPERATING_CASH_FLOW", "INVESTING_CASH_FLOW", "FINANCING_CASH_FLOW", "CAPITAL_EXPENDITURE", "FREE_CASH_FLOW"):
                cash_flow[name] = m
            else:
                ratios[name] = m

        return ExtractedFinancials(
            document_id=document_id,
            company_name=detected_company,
            fiscal_year=detected_fy,
            is_consolidated=detected_scope,
            income_statement=income_stmt,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            ratios=ratios,
        )

    def _parse_table_chunk(
        self,
        chunk: Dict[str, Any],
        document_id: str,
        filename: str,
        currency: str,
        unit: str,
        fiscal_year: int,
        is_consolidated: bool,
    ) -> List[ExtractedMetric]:
        """Extract line items from Markdown table format."""
        text = chunk.get("text", "")
        page_num = chunk.get("page_number", 1)
        metrics: List[ExtractedMetric] = []

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if not line.startswith("|") or "---" in line:
                continue

            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) < 2:
                continue

            raw_label = cells[0]
            canonical_name = FinancialNormalizer.match_canonical_metric(raw_label)
            if not canonical_name:
                continue

            # Check remaining cells for numeric candidate
            val: Optional[Decimal] = None
            raw_val_str = ""
            for cell in cells[1:]:
                parsed = FinancialNormalizer.parse_numeric_value(cell)
                if parsed is not None:
                    val = parsed
                    raw_val_str = cell
                    break

            if val is not None:
                # Determine statement type
                stmt_type = FinancialStatementType.INCOME_STATEMENT
                if canonical_name in ("TOTAL_ASSETS", "CURRENT_ASSETS", "TOTAL_DEBT", "SHAREHOLDERS_EQUITY"):
                    stmt_type = FinancialStatementType.BALANCE_SHEET
                elif canonical_name in ("OPERATING_CASH_FLOW", "INVESTING_CASH_FLOW", "CAPITAL_EXPENDITURE"):
                    stmt_type = FinancialStatementType.CASH_FLOW

                metrics.append(
                    ExtractedMetric(
                        name=canonical_name,
                        value=val,
                        raw_text=raw_val_str,
                        currency=currency,
                        unit=unit,
                        fiscal_year=fiscal_year,
                        period=ReportingPeriod.ANNUAL,
                        is_consolidated=is_consolidated,
                        citation=SourceCitation(
                            document_id=document_id,
                            filename=filename,
                            page_number=page_num,
                            exact_quote=f"{raw_label}: {raw_val_str}",
                            is_calculated=False,
                        ),
                        is_calculated=False,
                    )
                )

        return metrics

    def _parse_text_chunk(
        self,
        chunk: Dict[str, Any],
        document_id: str,
        filename: str,
        currency: str,
        unit: str,
        fiscal_year: int,
        is_consolidated: bool,
    ) -> List[ExtractedMetric]:
        """Extract canonical line items from unstructured text chunk lines."""
        text = chunk.get("text", "")
        page_num = chunk.get("page_number", 1)
        metrics: List[ExtractedMetric] = []

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            line_lower = line.lower()
            matched_canonical = None
            matched_label = None

            for label, canonical in sorted(CANONICAL_METRIC_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                pattern = r'(?:^|[\s:;•\-])' + re.escape(label) + r'(?:[\s:;•\-]|$)'
                if re.search(pattern, line_lower):
                    matched_canonical = canonical
                    matched_label = label
                    break

            if not matched_canonical:
                continue

            # Look for numbers on this line
            numbers = re.findall(r'\(?\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\)?', line)
            if not numbers:
                continue

            val = FinancialNormalizer.parse_numeric_value(numbers[0])
            if val is not None and val > 0:
                metrics.append(
                    ExtractedMetric(
                        name=matched_canonical,
                        value=val,
                        raw_text=numbers[0],
                        currency=currency,
                        unit=unit,
                        fiscal_year=fiscal_year,
                        period=ReportingPeriod.ANNUAL,
                        is_consolidated=is_consolidated,
                        citation=SourceCitation(
                            document_id=document_id,
                            filename=filename,
                            page_number=page_num,
                            exact_quote=line[:200],
                            is_calculated=False,
                        ),
                        is_calculated=False,
                    )
                )

        return metrics

    def _extract_with_llm(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str,
        filename: str,
        currency: str,
        unit: str,
        fiscal_year: int,
        is_consolidated: bool,
    ) -> List[ExtractedMetric]:
        """Use LLM assistance to extract metrics from narrative disclosures and statements."""
        # Provide sample of most informative chunks (tables and statements)
        sample_texts = "\n---\n".join([c.get("text", "")[:400] for c in chunks[:12]])

        prompt = f"""
Analyze the following financial document excerpts and extract core financial figures.
Return a clean JSON object with a 'metrics' array:
[
  {{
    "name": "REVENUE" | "GROSS_PROFIT" | "NET_INCOME" | "TOTAL_ASSETS" | "CURRENT_ASSETS" | "CURRENT_LIABILITIES" | "TOTAL_DEBT" | "SHAREHOLDERS_EQUITY" | "OPERATING_CASH_FLOW" | "CAPITAL_EXPENDITURE",
    "source_label": "exact line item label in report",
    "value": "12345.00",
    "statement": "INCOME_STATEMENT" | "BALANCE_SHEET" | "CASH_FLOW",
    "page_number": 1,
    "quote": "exact sentence or line from document"
  }}
]

Document Excerpts:
{sample_texts}
"""
        system_instruction = "You are an expert financial auditor. Extract exact reported numbers. Never fabricate or guess figures."

        metrics: List[ExtractedMetric] = []
        try:
            resp = self.llm.generate(prompt=prompt, system_instruction=system_instruction)
            data = resp.json()
            raw_list = data.get("metrics", [])
            for item in raw_list:
                name = item.get("name")
                val = FinancialNormalizer.parse_numeric_value(str(item.get("value", "")))
                page = int(item.get("page_number", 1))
                quote = str(item.get("quote", item.get("source_label", "")))

                if name and val is not None:
                    metrics.append(
                        ExtractedMetric(
                            name=name,
                            value=val,
                            raw_text=str(item.get("value")),
                            currency=currency,
                            unit=unit,
                            fiscal_year=fiscal_year,
                            period=ReportingPeriod.ANNUAL,
                            is_consolidated=is_consolidated,
                            citation=SourceCitation(
                                document_id=document_id,
                                filename=filename,
                                page_number=page,
                                exact_quote=quote,
                                is_calculated=False,
                            ),
                            is_calculated=False,
                        )
                    )
        except Exception as e:
            logger.warning("LLM metric extraction encountered an issue: %s", e)

        return metrics

    def _infer_company_name(self, chunks: List[Dict[str, Any]], filename: str) -> str:
        """Infer company name from first page text or filename."""
        if chunks:
            p1_text = chunks[0].get("text", "")
            for line in p1_text.splitlines()[:6]:
                stripped = line.strip()
                if "limited" in stripped.lower() or "inc." in stripped.lower() or "corp" in stripped.lower():
                    return stripped
        # Fallback from filename
        clean_name = filename.replace(".pdf", "").replace("_", " ").title()
        return clean_name

