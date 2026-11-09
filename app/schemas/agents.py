"""Pydantic schemas and interface contracts for all six specialized AI agents.

These models define the strict communication contracts, source citations,
and typed states for LangGraph orchestration in Milestone 2+.
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# Citation & Grounding Primitive
# ==============================================================================

class SourceCitation(BaseModel):
    """Source grounding reference ensuring zero ungrounded fabrication."""
    document_id: str
    filename: str
    page_number: int
    exact_quote: str = Field(..., description="Verbatim text quote from source document")
    table_index: Optional[int] = None
    is_calculated: bool = False
    calculation_basis: Optional[str] = None


# ==============================================================================
# Agent 2: Financial Extraction Agent Contracts
# ==============================================================================

class FinancialStatementType(str, Enum):
    INCOME_STATEMENT = "INCOME_STATEMENT"
    BALANCE_SHEET = "BALANCE_SHEET"
    CASH_FLOW = "CASH_FLOW"
    KEY_RATIOS = "KEY_RATIOS"


class ReportingPeriod(str, Enum):
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"
    HALF_YEAR = "HALF_YEAR"


class ExtractedMetric(BaseModel):
    name: str = Field(..., description="Canonical metric name, e.g. REVENUE, NET_INCOME")
    value: Decimal = Field(..., description="Exact numerical value extracted using Python Decimal")
    raw_text: str = Field(..., description="Raw string as printed in the report")
    currency: str = Field(default="INR", description="Currency symbol/code, e.g. INR, USD")
    unit: str = Field(default="CRORES", description="Unit of measurement: CRORES, MILLIONS, BILLIONS, THOUSANDS")
    fiscal_year: int
    period: ReportingPeriod
    is_consolidated: bool = True
    citation: SourceCitation
    is_calculated: bool = False
    formula: Optional[str] = None


class ExtractedFinancials(BaseModel):
    document_id: str
    company_name: str
    fiscal_year: int
    is_consolidated: bool
    income_statement: Dict[str, ExtractedMetric] = Field(default_factory=dict)
    balance_sheet: Dict[str, ExtractedMetric] = Field(default_factory=dict)
    cash_flow: Dict[str, ExtractedMetric] = Field(default_factory=dict)
    ratios: Dict[str, ExtractedMetric] = Field(default_factory=dict)


# ==============================================================================
# Agent 3: Red Flag Agent Contracts
# ==============================================================================

class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskCategory(str, Enum):
    DEBT_AND_LEVERAGE = "DEBT_AND_LEVERAGE"
    PROFITABILITY_DECLINE = "PROFITABILITY_DECLINE"
    CASH_FLOW_DIVERGENCE = "CASH_FLOW_DIVERGENCE"
    LIQUIDITY_DETERIORATION = "LIQUIDITY_DETERIORATION"
    AUDITOR_QUALIFICATION = "AUDITOR_QUALIFICATION"
    GOING_CONCERN = "GOING_CONCERN"
    ACCOUNTING_ANOMALY = "ACCOUNTING_ANOMALY"
    CONTINGENT_LIABILITIES = "CONTINGENT_LIABILITIES"


class RedFlagFinding(BaseModel):
    finding_id: str
    category: RiskCategory
    severity: RiskSeverity
    title: str
    description: str
    supporting_evidence: str
    reason_for_classification: str
    relevant_period: str
    source_citation: SourceCitation


# ==============================================================================
# Agent 4: Comparison Agent Contracts
# ==============================================================================

class MetricComparisonItem(BaseModel):
    metric_name: str
    company_a_val: Decimal
    company_b_val: Decimal
    variance_nominal: Decimal
    variance_percentage: Optional[Decimal] = None
    unit: str
    note: Optional[str] = None


class ComparisonResult(BaseModel):
    comparison_id: str
    company_a: str
    company_b: str
    period: str
    normalized_currency: str
    metric_comparisons: List[MetricComparisonItem]
    comparative_summary: str
    limitations: List[str] = Field(default_factory=list)


# ==============================================================================
# Agent 5: Research Agent Contracts
# ==============================================================================

class ResearchAnswer(BaseModel):
    question: str
    direct_facts: List[str] = Field(default_factory=list)
    calculated_values: List[str] = Field(default_factory=list)
    analytical_conclusions: List[str] = Field(default_factory=list)
    unavailable_information: List[str] = Field(default_factory=list)
    citations: List[SourceCitation] = Field(default_factory=list)


# ==============================================================================
# Agent 6: Report Agent Contracts
# ==============================================================================

class FinancialReportSection(BaseModel):
    section_title: str
    content_markdown: str
    citations: List[SourceCitation] = Field(default_factory=list)


class FinancialReport(BaseModel):
    report_id: str
    company_name: str
    report_title: str
    fiscal_period: str
    generated_at: str
    executive_summary: str
    company_overview: str
    key_financials_summary: str
    financial_performance: str
    red_flags_and_risks: str
    comparative_benchmarking: Optional[str] = None
    management_outlook: str
    sources_and_references: List[SourceCitation]

