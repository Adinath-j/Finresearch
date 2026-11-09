"""Unit tests for Deterministic Financial Risk Detection Rule Engine."""

import unittest
from decimal import Decimal
from app.agents.red_flag_agent.rule_engine import RuleEngine
from app.schemas.agents import (
    ExtractedFinancials,
    ExtractedMetric,
    ReportingPeriod,
    RiskCategory,
    RiskSeverity,
    SourceCitation,
)


class TestRuleEngine(unittest.TestCase):
    """Test suite verifying financial warning detection and anomaly classification."""

    def setUp(self):
        self.rule_engine = RuleEngine()

    def _create_metric(self, name: str, value: str, is_calc: bool = False) -> ExtractedMetric:
        return ExtractedMetric(
            name=name,
            value=Decimal(value),
            raw_text=value,
            currency="USD",
            unit="MILLIONS",
            fiscal_year=2025,
            period=ReportingPeriod.ANNUAL,
            is_consolidated=True,
            citation=SourceCitation(
                document_id="doc-test-rf",
                filename="statement.pdf",
                page_number=1,
                exact_quote=f"{name}: {value}",
                is_calculated=is_calc,
            ),
            is_calculated=is_calc,
        )

    def test_debt_to_equity_risk_trigger(self):
        # D/E = 2.8x > 2.0x threshold
        financials = ExtractedFinancials(
            document_id="doc-test-rf",
            company_name="Leveraged Corp",
            fiscal_year=2025,
            is_consolidated=True,
            balance_sheet={
                "TOTAL_DEBT": self._create_metric("TOTAL_DEBT", "2800"),
                "SHAREHOLDERS_EQUITY": self._create_metric("SHAREHOLDERS_EQUITY", "1000"),
            },
            ratios={
                "DEBT_TO_EQUITY": self._create_metric("DEBT_TO_EQUITY", "2.80", is_calc=True),
            },
        )

        findings = self.rule_engine.evaluate_financials(financials)
        debt_findings = [f for f in findings if f.category == RiskCategory.DEBT_AND_LEVERAGE]
        self.assertEqual(len(debt_findings), 1)
        self.assertEqual(debt_findings[0].severity, RiskSeverity.MEDIUM)
        self.assertIn("High Debt-to-Equity", debt_findings[0].title)

    def test_deficient_current_ratio_risk_trigger(self):
        # Current Ratio = 0.75x < 1.0x threshold
        financials = ExtractedFinancials(
            document_id="doc-test-rf",
            company_name="Illiquid Corp",
            fiscal_year=2025,
            is_consolidated=True,
            balance_sheet={
                "CURRENT_ASSETS": self._create_metric("CURRENT_ASSETS", "750"),
                "CURRENT_LIABILITIES": self._create_metric("CURRENT_LIABILITIES", "1000"),
            },
            ratios={
                "CURRENT_RATIO": self._create_metric("CURRENT_RATIO", "0.75", is_calc=True),
            },
        )

        findings = self.rule_engine.evaluate_financials(financials)
        liq_findings = [f for f in findings if f.category == RiskCategory.LIQUIDITY_DETERIORATION]
        self.assertEqual(len(liq_findings), 1)
        self.assertEqual(liq_findings[0].severity, RiskSeverity.HIGH)
        self.assertIn("Current Ratio Below Par", liq_findings[0].title)

    def test_cash_flow_divergence_risk_trigger(self):
        # Positive Net Income (500) but Negative Operating Cash Flow (-200)
        financials = ExtractedFinancials(
            document_id="doc-test-rf",
            company_name="Aggressive Accrual Corp",
            fiscal_year=2025,
            is_consolidated=True,
            income_statement={
                "NET_INCOME": self._create_metric("NET_INCOME", "500"),
            },
            cash_flow={
                "OPERATING_CASH_FLOW": self._create_metric("OPERATING_CASH_FLOW", "-200"),
            },
        )

        findings = self.rule_engine.evaluate_financials(financials)
        cf_findings = [f for f in findings if f.category == RiskCategory.CASH_FLOW_DIVERGENCE]
        self.assertGreaterEqual(len(cf_findings), 1)
        self.assertEqual(cf_findings[0].severity, RiskSeverity.HIGH)
        self.assertIn("Negative Cash Flow from Operations", cf_findings[0].title)

    def test_pristine_financials_trigger_no_false_alarms(self):
        # Clean company: D/E = 0.25, Current Ratio = 2.1, OCF = 3000 > Net Income = 1000
        financials = ExtractedFinancials(
            document_id="doc-test-rf",
            company_name="Healthy Corp",
            fiscal_year=2025,
            is_consolidated=True,
            income_statement={
                "REVENUE": self._create_metric("REVENUE", "10000"),
                "NET_INCOME": self._create_metric("NET_INCOME", "1500"),
                "OPERATING_INCOME": self._create_metric("OPERATING_INCOME", "2000"),
            },
            balance_sheet={
                "CURRENT_ASSETS": self._create_metric("CURRENT_ASSETS", "4200"),
                "CURRENT_LIABILITIES": self._create_metric("CURRENT_LIABILITIES", "2000"),
                "TOTAL_DEBT": self._create_metric("TOTAL_DEBT", "1000"),
                "SHAREHOLDERS_EQUITY": self._create_metric("SHAREHOLDERS_EQUITY", "5000"),
            },
            cash_flow={
                "OPERATING_CASH_FLOW": self._create_metric("OPERATING_CASH_FLOW", "2200"),
                "CAPITAL_EXPENDITURE": self._create_metric("CAPITAL_EXPENDITURE", "800"),
            },
            ratios={
                "CURRENT_RATIO": self._create_metric("CURRENT_RATIO", "2.10", is_calc=True),
                "DEBT_TO_EQUITY": self._create_metric("DEBT_TO_EQUITY", "0.20", is_calc=True),
                "OPERATING_MARGIN": self._create_metric("OPERATING_MARGIN", "20.00", is_calc=True),
                "FREE_CASH_FLOW": self._create_metric("FREE_CASH_FLOW", "1400.00", is_calc=True),
            },
        )

        findings = self.rule_engine.evaluate_financials(financials)
        self.assertEqual(len(findings), 0)


if __name__ == "__main__":
    unittest.main()

