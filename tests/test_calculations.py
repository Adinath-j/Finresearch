"""Unit tests for Deterministic Financial Calculations Engine using Python Decimal."""

import unittest
from decimal import Decimal
from app.agents.extraction_agent.calculations import FinancialCalculations, to_decimal


class TestFinancialCalculations(unittest.TestCase):
    """Test suite verifying arithmetic precision with Python Decimal."""

    def test_to_decimal(self):
        self.assertEqual(to_decimal("1,500.50"), Decimal("1500.50"))
        self.assertEqual(to_decimal(100), Decimal("100"))
        self.assertIsNone(to_decimal("-"))
        self.assertIsNone(to_decimal("N/A"))
        self.assertIsNone(to_decimal(None))

    def test_gross_margin(self):
        rev = Decimal("1000")
        gp = Decimal("400")
        margin = FinancialCalculations.calculate_gross_margin(rev, gp)
        self.assertEqual(margin, Decimal("40.00"))

        # Zero revenue should safely return None without throwing DivisionByZero
        self.assertIsNone(FinancialCalculations.calculate_gross_margin(Decimal("0"), gp))

    def test_operating_margin(self):
        rev = Decimal("14300")
        op_inc = Decimal("1600")
        margin = FinancialCalculations.calculate_operating_margin(rev, op_inc)
        self.assertEqual(margin, Decimal("11.19"))

    def test_net_profit_margin(self):
        rev = Decimal("153670")
        net_inc = Decimal("26248")
        margin = FinancialCalculations.calculate_net_profit_margin(rev, net_inc)
        self.assertEqual(margin, Decimal("17.08"))

    def test_current_ratio(self):
        ca = Decimal("7950")
        cl = Decimal("5000")
        cr = FinancialCalculations.calculate_current_ratio(ca, cl)
        self.assertEqual(cr, Decimal("1.59"))

        # Deficient current ratio
        cr_bad = FinancialCalculations.calculate_current_ratio(Decimal("4000"), Decimal("5000"))
        self.assertEqual(cr_bad, Decimal("0.80"))

    def test_debt_to_equity(self):
        debt = Decimal("2500")
        equity = Decimal("9900")
        de = FinancialCalculations.calculate_debt_to_equity(debt, equity)
        self.assertEqual(de, Decimal("0.25"))

        # Highly leveraged firm
        de_high = FinancialCalculations.calculate_debt_to_equity(Decimal("25000"), Decimal("10000"))
        self.assertEqual(de_high, Decimal("2.50"))

    def test_return_on_equity(self):
        net_inc = Decimal("1184")
        equity = Decimal("9900")
        roe = FinancialCalculations.calculate_return_on_equity(net_inc, equity)
        self.assertEqual(roe, Decimal("11.96"))

    def test_free_cash_flow(self):
        ocf = Decimal("3150")
        capex = Decimal("1400")
        fcf = FinancialCalculations.calculate_free_cash_flow(ocf, capex)
        self.assertEqual(fcf, Decimal("1750.00"))

        # Capex represented as negative in accounting statement
        fcf_neg_capex = FinancialCalculations.calculate_free_cash_flow(ocf, Decimal("-1400"))
        self.assertEqual(fcf_neg_capex, Decimal("1750.00"))

    def test_yoy_growth(self):
        curr = Decimal("14300")
        prior = Decimal("11800")
        growth = FinancialCalculations.calculate_yoy_growth(curr, prior)
        self.assertEqual(growth, Decimal("21.19"))

    def test_compute_all_ratios_integration(self):
        metrics = {
            "REVENUE": Decimal("14300"),
            "GROSS_PROFIT": Decimal("9750"),
            "OPERATING_INCOME": Decimal("1600"),
            "NET_INCOME": Decimal("1184"),
            "CURRENT_ASSETS": Decimal("7950"),
            "CURRENT_LIABILITIES": Decimal("5000"),
            "TOTAL_DEBT": Decimal("2500"),
            "SHAREHOLDERS_EQUITY": Decimal("9900"),
            "OPERATING_CASH_FLOW": Decimal("3150"),
            "CAPITAL_EXPENDITURE": Decimal("1400"),
        }
        ratios = FinancialCalculations.compute_all_ratios(metrics)
        self.assertIn("GROSS_MARGIN", ratios)
        self.assertIn("OPERATING_MARGIN", ratios)
        self.assertIn("NET_PROFIT_MARGIN", ratios)
        self.assertIn("CURRENT_RATIO", ratios)
        self.assertIn("DEBT_TO_EQUITY", ratios)
        self.assertIn("RETURN_ON_EQUITY", ratios)
        self.assertIn("FREE_CASH_FLOW", ratios)

        self.assertEqual(ratios["CURRENT_RATIO"][0], Decimal("1.59"))
        self.assertEqual(ratios["FREE_CASH_FLOW"][0], Decimal("1750.00"))


if __name__ == "__main__":
    unittest.main()

