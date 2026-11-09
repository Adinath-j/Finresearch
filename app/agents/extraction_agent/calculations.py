"""Deterministic Financial Calculations Engine using Python Decimal.

Enforces zero floating-point drift and validates all inputs and denominators.
"""

from decimal import Decimal, InvalidOperation, DivisionByZero
from typing import Any, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def to_decimal(val: Any) -> Optional[Decimal]:
    """Safely cast string, float, or integer to Python Decimal."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        clean_str = str(val).replace(",", "").strip()
        if not clean_str or clean_str.lower() in ("nan", "none", "null", "-", "n/a"):
            return None
        return Decimal(clean_str)
    except (InvalidOperation, ValueError, TypeError):
        return None


class FinancialCalculations:
    """Computes standard corporate financial ratios and indicators deterministically."""

    @staticmethod
    def calculate_gross_margin(revenue: Decimal, gross_profit: Decimal) -> Optional[Decimal]:
        """Gross Profit Margin = (Gross Profit / Revenue) * 100"""
        if revenue is None or gross_profit is None or revenue <= Decimal("0"):
            return None
        return round((gross_profit / revenue) * Decimal("100"), 2)

    @staticmethod
    def calculate_operating_margin(revenue: Decimal, operating_income: Decimal) -> Optional[Decimal]:
        """Operating Profit Margin = (Operating Income / Revenue) * 100"""
        if revenue is None or operating_income is None or revenue <= Decimal("0"):
            return None
        return round((operating_income / revenue) * Decimal("100"), 2)

    @staticmethod
    def calculate_net_profit_margin(revenue: Decimal, net_income: Decimal) -> Optional[Decimal]:
        """Net Profit Margin = (Net Income / Revenue) * 100"""
        if revenue is None or net_income is None or revenue <= Decimal("0"):
            return None
        return round((net_income / revenue) * Decimal("100"), 2)

    @staticmethod
    def calculate_current_ratio(current_assets: Decimal, current_liabilities: Decimal) -> Optional[Decimal]:
        """Current Ratio = Current Assets / Current Liabilities"""
        if current_assets is None or current_liabilities is None or current_liabilities <= Decimal("0"):
            return None
        return round(current_assets / current_liabilities, 2)

    @staticmethod
    def calculate_quick_ratio(
        current_assets: Decimal,
        inventory: Optional[Decimal],
        current_liabilities: Decimal,
    ) -> Optional[Decimal]:
        """Quick Ratio = (Current Assets - Inventory) / Current Liabilities"""
        if current_assets is None or current_liabilities is None or current_liabilities <= Decimal("0"):
            return None
        liquid_assets = current_assets - (inventory or Decimal("0"))
        return round(liquid_assets / current_liabilities, 2)

    @staticmethod
    def calculate_debt_to_equity(total_debt: Decimal, shareholders_equity: Decimal) -> Optional[Decimal]:
        """Debt-to-Equity Ratio = Total Debt / Shareholders' Equity"""
        if total_debt is None or shareholders_equity is None or shareholders_equity <= Decimal("0"):
            return None
        return round(total_debt / shareholders_equity, 2)

    @staticmethod
    def calculate_return_on_equity(net_income: Decimal, shareholders_equity: Decimal) -> Optional[Decimal]:
        """Return on Equity (RoE) = (Net Income / Shareholders' Equity) * 100"""
        if net_income is None or shareholders_equity is None or shareholders_equity <= Decimal("0"):
            return None
        return round((net_income / shareholders_equity) * Decimal("100"), 2)

    @staticmethod
    def calculate_free_cash_flow(operating_cash_flow: Decimal, capital_expenditure: Decimal) -> Optional[Decimal]:
        """Free Cash Flow (FCF) = Operating Cash Flow - Capital Expenditure"""
        if operating_cash_flow is None or capital_expenditure is None:
            return None
        # Capex is treated as an outflow (subtracted)
        return round(operating_cash_flow - abs(capital_expenditure), 2)

    @staticmethod
    def calculate_yoy_growth(current_val: Decimal, prior_val: Decimal) -> Optional[Decimal]:
        """Year-over-Year Growth Rate = ((Current - Prior) / Prior) * 100"""
        if current_val is None or prior_val is None or prior_val == Decimal("0"):
            return None
        return round(((current_val - prior_val) / abs(prior_val)) * Decimal("100"), 2)

    @classmethod
    def compute_all_ratios(cls, metrics: Dict[str, Decimal]) -> Dict[str, Tuple[Decimal, str]]:
        """Compute all calculable financial ratios from a dictionary of known metrics.

        Returns:
            Dict mapping ratio_name -> (Decimal_value, formula_string)
        """
        results: Dict[str, Tuple[Decimal, str]] = {}

        rev = metrics.get("REVENUE")
        gp = metrics.get("GROSS_PROFIT")
        op_inc = metrics.get("OPERATING_INCOME")
        net_inc = metrics.get("NET_INCOME")
        ca = metrics.get("CURRENT_ASSETS")
        cl = metrics.get("CURRENT_LIABILITIES")
        debt = metrics.get("TOTAL_DEBT")
        equity = metrics.get("SHAREHOLDERS_EQUITY")
        ocf = metrics.get("OPERATING_CASH_FLOW")
        capex = metrics.get("CAPITAL_EXPENDITURE")

        # 1. Margins
        if rev and gp:
            gm = cls.calculate_gross_margin(rev, gp)
            if gm is not None:
                results["GROSS_MARGIN"] = (gm, "(GROSS_PROFIT / REVENUE) * 100")

        if rev and op_inc:
            om = cls.calculate_operating_margin(rev, op_inc)
            if om is not None:
                results["OPERATING_MARGIN"] = (om, "(OPERATING_INCOME / REVENUE) * 100")

        if rev and net_inc:
            npm = cls.calculate_net_profit_margin(rev, net_inc)
            if npm is not None:
                results["NET_PROFIT_MARGIN"] = (npm, "(NET_INCOME / REVENUE) * 100")

        # 2. Solvency & Liquidity
        if ca and cl:
            cr = cls.calculate_current_ratio(ca, cl)
            if cr is not None:
                results["CURRENT_RATIO"] = (cr, "CURRENT_ASSETS / CURRENT_LIABILITIES")

        if debt and equity:
            de = cls.calculate_debt_to_equity(debt, equity)
            if de is not None:
                results["DEBT_TO_EQUITY"] = (de, "TOTAL_DEBT / SHAREHOLDERS_EQUITY")

        if net_inc and equity:
            roe = cls.calculate_return_on_equity(net_inc, equity)
            if roe is not None:
                results["RETURN_ON_EQUITY"] = (roe, "(NET_INCOME / SHAREHOLDERS_EQUITY) * 100")

        # 3. Cash Flow
        if ocf and capex:
            fcf = cls.calculate_free_cash_flow(ocf, capex)
            if fcf is not None:
                results["FREE_CASH_FLOW"] = (fcf, "OPERATING_CASH_FLOW - CAPITAL_EXPENDITURE")

        return results
