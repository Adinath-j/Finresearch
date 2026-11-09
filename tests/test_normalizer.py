"""Unit tests for Financial Normalization Engine."""

import unittest
from decimal import Decimal
from app.agents.extraction_agent.normalizer import FinancialNormalizer


class TestFinancialNormalizer(unittest.TestCase):
    """Test suite for parsing accounting conventions, units, and canonical mapping."""

    def test_parse_accounting_parentheses(self):
        # (120) should parse to -120
        val = FinancialNormalizer.parse_numeric_value("(120)")
        self.assertEqual(val, Decimal("-120"))

        val_spaced = FinancialNormalizer.parse_numeric_value(" ( 1,450.50 ) ")
        self.assertEqual(val_spaced, Decimal("-1450.50"))

    def test_parse_currency_and_commas(self):
        val_usd = FinancialNormalizer.parse_numeric_value("$14,300.00")
        self.assertEqual(val_usd, Decimal("14300.00"))

        val_inr = FinancialNormalizer.parse_numeric_value("₹ 1,53,670")
        self.assertEqual(val_inr, Decimal("153670"))

    def test_parse_missing_and_blank(self):
        self.assertIsNone(FinancialNormalizer.parse_numeric_value("-"))
        self.assertIsNone(FinancialNormalizer.parse_numeric_value("N/A"))
        self.assertIsNone(FinancialNormalizer.parse_numeric_value("Nil"))
        self.assertIsNone(FinancialNormalizer.parse_numeric_value(""))

    def test_detect_currency(self):
        self.assertEqual(FinancialNormalizer.detect_currency("Amounts in INR (₹) Crores"), "INR")
        self.assertEqual(FinancialNormalizer.detect_currency("Statements of Operations in USD Millions ($)"), "USD")
        self.assertEqual(FinancialNormalizer.detect_currency("Financial results in Euro (€)"), "EUR")

    def test_detect_unit(self):
        self.assertEqual(FinancialNormalizer.detect_unit("In ₹ Crore"), "CRORES")
        self.assertEqual(FinancialNormalizer.detect_unit("In Millions of USD"), "MILLIONS")
        self.assertEqual(FinancialNormalizer.detect_unit("In Thousands"), "THOUSANDS")

    def test_detect_reporting_scope(self):
        self.assertTrue(FinancialNormalizer.detect_reporting_scope("Consolidated Balance Sheet as of March 31"))
        self.assertFalse(FinancialNormalizer.detect_reporting_scope("Standalone Statement of Profit and Loss"))

    def test_match_canonical_metric(self):
        self.assertEqual(FinancialNormalizer.match_canonical_metric("Revenue from operations"), "REVENUE")
        self.assertEqual(FinancialNormalizer.match_canonical_metric("Total Revenue"), "REVENUE")
        self.assertEqual(FinancialNormalizer.match_canonical_metric("Cost of goods sold"), "COGS")
        self.assertEqual(FinancialNormalizer.match_canonical_metric("Profit for the period"), "NET_INCOME")
        self.assertEqual(FinancialNormalizer.match_canonical_metric("Total current assets"), "CURRENT_ASSETS")
        self.assertEqual(FinancialNormalizer.match_canonical_metric("Long-term debt"), "TOTAL_DEBT")
        self.assertEqual(FinancialNormalizer.match_canonical_metric("Net cash from operating activities"), "OPERATING_CASH_FLOW")
        self.assertIsNone(FinancialNormalizer.match_canonical_metric("Random Unrelated Line"))


if __name__ == "__main__":
    unittest.main()

