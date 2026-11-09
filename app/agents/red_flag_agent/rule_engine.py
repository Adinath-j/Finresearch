"""Deterministic Financial Risk Detection Rule Engine.

Evaluates standardized financial metrics against solvency, profitability,
cash flow, and liquidity risk rules using Python Decimal.
"""

from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.schemas.agents import (
    ExtractedFinancials,
    ExtractedMetric,
    RedFlagFinding,
    RiskCategory,
    RiskSeverity,
    SourceCitation,
)

logger = logging.getLogger(__name__)


class RuleEngine:
    """Evaluates extracted financial metrics for warning indicators and risk anomalies."""

    def __init__(
        self,
        max_debt_to_equity: Decimal = Decimal("2.0"),
        min_current_ratio: Decimal = Decimal("1.0"),
        min_operating_margin: Decimal = Decimal("5.0"),
    ):
        self.max_debt_to_equity = max_debt_to_equity
        self.min_current_ratio = min_current_ratio
        self.min_operating_margin = min_operating_margin

    def evaluate_financials(
        self,
        financials: ExtractedFinancials,
    ) -> List[RedFlagFinding]:
        """Apply deterministic financial rules to extracted metrics."""
        findings: List[RedFlagFinding] = []
        doc_id = financials.document_id
        period_str = f"FY {financials.fiscal_year}"

        # Combine all metrics for unified access
        metrics: Dict[str, ExtractedMetric] = {}
        metrics.update(financials.income_statement)
        metrics.update(financials.balance_sheet)
        metrics.update(financials.cash_flow)
        metrics.update(financials.ratios)

        # 1. Solvency Rule: High Debt-to-Equity
        de_metric = metrics.get("DEBT_TO_EQUITY")
        if de_metric and de_metric.value > self.max_debt_to_equity:
            findings.append(
                RedFlagFinding(
                    finding_id=uuid4().hex,
                    category=RiskCategory.DEBT_AND_LEVERAGE,
                    severity=RiskSeverity.HIGH if de_metric.value > Decimal("3.0") else RiskSeverity.MEDIUM,
                    title="Elevated Leverage / High Debt-to-Equity Ratio",
                    description=(
                        f"The company's Debt-to-Equity ratio of {de_metric.value} exceeds the standard "
                        f"prudential threshold of {self.max_debt_to_equity}x, indicating reliance on debt financing."
                    ),
                    supporting_evidence=f"Debt-to-Equity: {de_metric.value}x",
                    reason_for_classification="Total debt significantly exceeds total shareholders' equity.",
                    relevant_period=period_str,
                    source_citation=de_metric.citation,
                )
            )

        # 2. Liquidity Rule: Deteriorating Current Ratio
        cr_metric = metrics.get("CURRENT_RATIO")
        if cr_metric and cr_metric.value < self.min_current_ratio:
            findings.append(
                RedFlagFinding(
                    finding_id=uuid4().hex,
                    category=RiskCategory.LIQUIDITY_DETERIORATION,
                    severity=RiskSeverity.HIGH,
                    title="Deficient Liquidity / Current Ratio Below Par",
                    description=(
                        f"Current Ratio of {cr_metric.value}x is below the safe threshold of {self.min_current_ratio}x. "
                        f"Current liabilities exceed liquid current assets, indicating near-term working capital pressure."
                    ),
                    supporting_evidence=f"Current Ratio: {cr_metric.value}x",
                    reason_for_classification="Current liabilities exceed current assets.",
                    relevant_period=period_str,
                    source_citation=cr_metric.citation,
                )
            )

        # 3. Cash Flow Divergence: Negative Operating Cash Flow vs Positive Net Income
        ocf_metric = metrics.get("OPERATING_CASH_FLOW")
        ni_metric = metrics.get("NET_INCOME")
        if ocf_metric and ni_metric:
            if ocf_metric.value < Decimal("0") and ni_metric.value > Decimal("0"):
                findings.append(
                    RedFlagFinding(
                        finding_id=uuid4().hex,
                        category=RiskCategory.CASH_FLOW_DIVERGENCE,
                        severity=RiskSeverity.HIGH,
                        title="Earnings Quality Risk: Negative Cash Flow from Operations",
                        description=(
                            f"The company reported positive Net Income ({ni_metric.value} {ni_metric.unit}) but negative "
                            f"Cash Flow from Operations ({ocf_metric.value} {ocf_metric.unit}). This divergence indicates "
                            f"potential aggressive revenue recognition or substantial uncollected receivables."
                        ),
                        supporting_evidence=f"Net Income: {ni_metric.value}, Operating Cash Flow: {ocf_metric.value}",
                        reason_for_classification="Operating cash generation fails to support reported accounting profits.",
                        relevant_period=period_str,
                        source_citation=ocf_metric.citation,
                    )
                )

        # 4. Free Cash Flow: Negative FCF
        fcf_metric = metrics.get("FREE_CASH_FLOW")
        if fcf_metric and fcf_metric.value < Decimal("0"):
            findings.append(
                RedFlagFinding(
                    finding_id=uuid4().hex,
                    category=RiskCategory.CASH_FLOW_DIVERGENCE,
                    severity=RiskSeverity.MEDIUM,
                    title="Negative Free Cash Flow",
                    description=(
                        f"Free Cash Flow is negative at {fcf_metric.value} {fcf_metric.unit}. Capital expenditures "
                        f"exceeded operating cash generation for the period."
                    ),
                    supporting_evidence=f"Free Cash Flow: {fcf_metric.value}",
                    reason_for_classification="Capital investments exceed operating cash inflow.",
                    relevant_period=period_str,
                    source_citation=fcf_metric.citation,
                )
            )

        # 5. Profitability Rule: Operating Margin Compression or Loss
        op_metric = metrics.get("OPERATING_MARGIN")
        if op_metric and op_metric.value < self.min_operating_margin:
            severity = RiskSeverity.HIGH if op_metric.value < Decimal("0") else RiskSeverity.MEDIUM
            findings.append(
                RedFlagFinding(
                    finding_id=uuid4().hex,
                    category=RiskCategory.PROFITABILITY_DECLINE,
                    severity=severity,
                    title="Low or Negative Operating Profit Margin",
                    description=(
                        f"Operating margin of {op_metric.value}% is below the minimum threshold of "
                        f"{self.min_operating_margin}%, reflecting cost pressures or operating losses."
                    ),
                    supporting_evidence=f"Operating Margin: {op_metric.value}%",
                    reason_for_classification="Operating margin compressed below baseline operational efficiency.",
                    relevant_period=period_str,
                    source_citation=op_metric.citation,
                )
            )

        # 6. Bottom-line Loss: Negative Net Income
        if ni_metric and ni_metric.value < Decimal("0"):
            findings.append(
                RedFlagFinding(
                    finding_id=uuid4().hex,
                    category=RiskCategory.PROFITABILITY_DECLINE,
                    severity=RiskSeverity.HIGH,
                    title="Net Operating Loss (Negative Net Income)",
                    description=(
                        f"The company recorded a net loss of {ni_metric.value} {ni_metric.unit} for the fiscal period."
                    ),
                    supporting_evidence=f"Net Income: {ni_metric.value} {ni_metric.unit}",
                    reason_for_classification="Reported accounting profit is negative.",
                    relevant_period=period_str,
                    source_citation=ni_metric.citation,
                )
            )

        return findings

