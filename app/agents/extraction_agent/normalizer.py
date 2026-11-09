"""Financial Normalization Engine.

Parses accounting strings into Decimal numbers, resolves units and currencies,
identifies reporting scope (Consolidated vs Standalone), and maps line labels to canonical taxonomy.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

CANONICAL_METRIC_MAP: Dict[str, str] = {
    # Income Statement
    "revenue": "REVENUE",
    "revenue from operations": "REVENUE",
    "total revenue": "REVENUE",
    "operating revenue": "REVENUE",
    "turnover": "REVENUE",
    "subscription revenue": "REVENUE",
    "net sales": "REVENUE",
    "cost of goods sold": "COGS",
    "cost of revenue": "COGS",
    "cost of materials consumed": "COGS",
    "gross profit": "GROSS_PROFIT",
    "operating expenses": "OPERATING_EXPENSES",
    "total operating expenses": "OPERATING_EXPENSES",
    "operating income": "OPERATING_INCOME",
    "operating profit": "OPERATING_INCOME",
    "operating profit before working capital": "OPERATING_INCOME",
    "ebit": "OPERATING_INCOME",
    "ebitda": "EBITDA",
    "profit before tax": "PROFIT_BEFORE_TAX",
    "profit before income tax": "PROFIT_BEFORE_TAX",
    "income before taxes": "PROFIT_BEFORE_TAX",
    "net income": "NET_INCOME",
    "net profit": "NET_INCOME",
    "profit for the period": "NET_INCOME",
    "profit for the year": "NET_INCOME",
    "diluted earnings per share": "EPS_DILUTED",
    "diluted eps": "EPS_DILUTED",
    # Balance Sheet
    "total assets": "TOTAL_ASSETS",
    "total current assets": "CURRENT_ASSETS",
    "current assets": "CURRENT_ASSETS",
    "total non-current assets": "NON_CURRENT_ASSETS",
    "total non current assets": "NON_CURRENT_ASSETS",
    "non-current assets": "NON_CURRENT_ASSETS",
    "non current assets": "NON_CURRENT_ASSETS",
    "noncurrent assets": "NON_CURRENT_ASSETS",
    "total liabilities": "TOTAL_LIABILITIES",
    "total current liabilities": "CURRENT_LIABILITIES",
    "current liabilities": "CURRENT_LIABILITIES",
    "total non-current liabilities": "NON_CURRENT_LIABILITIES",
    "total non current liabilities": "NON_CURRENT_LIABILITIES",
    "non-current liabilities": "NON_CURRENT_LIABILITIES",
    "non current liabilities": "NON_CURRENT_LIABILITIES",
    "noncurrent liabilities": "NON_CURRENT_LIABILITIES",
    "total debt": "TOTAL_DEBT",
    "long-term debt": "TOTAL_DEBT",
    "long term debt": "TOTAL_DEBT",
    "longterm debt": "TOTAL_DEBT",
    "borrowings": "TOTAL_DEBT",
    "shareholders equity": "SHAREHOLDERS_EQUITY",
    "total stockholders equity": "SHAREHOLDERS_EQUITY",
    "total equity": "SHAREHOLDERS_EQUITY",
    "equity share capital": "SHAREHOLDERS_EQUITY",
    # Cash Flow
    "operating cash flow": "OPERATING_CASH_FLOW",
    "cash from operating activities": "OPERATING_CASH_FLOW",
    "net cash from operating activities": "OPERATING_CASH_FLOW",
    "investing cash flow": "INVESTING_CASH_FLOW",
    "cash from investing activities": "INVESTING_CASH_FLOW",
    "financing cash flow": "FINANCING_CASH_FLOW",
    "cash from financing activities": "FINANCING_CASH_FLOW",
    "capital expenditure": "CAPITAL_EXPENDITURE",
    "capital expenditures": "CAPITAL_EXPENDITURE",
    "purchase of property, plant and equipment": "CAPITAL_EXPENDITURE",
}


class FinancialNormalizer:
    """Normalizes financial numbers, accounting conventions, units, and periods."""

    @staticmethod
    def parse_numeric_value(raw_val: str) -> Optional[Decimal]:
        """Parse raw string into Python Decimal.

        Handles:
        - Accounting parentheses for negative numbers: `(120)` -> `-120.00`
        - Currency symbols and commas: `$1,250.50` -> `1250.50`, `₹ 1,53,670` -> `153670`
        - Dashes/blanks -> None
        """
        if not raw_val:
            return None

        clean = raw_val.strip()
        # Remove common currency and label noise
        clean = re.sub(r"[\$₹€£]|Rs\.?|INR|USD|EUR", "", clean, flags=re.IGNORECASE).strip()

        # Check for empty or N/A representations
        if clean in ("-", "—", "–", "N/A", "n/a", "nil", "Nil", "", "None", "null"):
            return None

        # Handle accounting parentheses: e.g. (1,234.56) or ( 1234 )
        is_negative = False
        paren_match = re.match(r"^\s*\(\s*([\d,\.]+)\s*\)\s*$", clean)
        if paren_match:
            is_negative = True
            clean = paren_match.group(1)
        elif clean.startswith("-") or clean.endswith("-"):
            is_negative = True
            clean = clean.replace("-", "").strip()

        # Remove commas and spaces
        clean = clean.replace(",", "").replace(" ", "")

        try:
            val = Decimal(clean)
            return -val if is_negative else val
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def detect_currency(text: str) -> str:
        """Identify primary reporting currency."""
        t_lower = text.lower()
        if "₹" in text or "rs." in t_lower or "inr" in t_lower or "rupees" in t_lower or "crore" in t_lower or "lakh" in t_lower:
            return "INR"
        if "$" in text or "usd" in t_lower or "dollars" in t_lower:
            return "USD"
        if "€" in text or "eur" in t_lower or "euro" in t_lower:
            return "EUR"
        if "£" in text or "gbp" in t_lower:
            return "GBP"
        return "INR"  # Default Indian context for Springboard

    @staticmethod
    def detect_unit(text: str) -> str:
        """Identify multiplier unit (e.g. CRORES, MILLIONS, THOUSANDS)."""
        t_lower = text.lower()
        if "crore" in t_lower or "cr." in t_lower:
            return "CRORES"
        if "lakh" in t_lower:
            return "LAKHS"
        if "billion" in t_lower:
            return "BILLIONS"
        if "million" in t_lower:
            return "MILLIONS"
        if "thousand" in t_lower:
            return "THOUSANDS"
        return "CRORES"

    @staticmethod
    def detect_reporting_scope(text: str) -> bool:
        """Return True if Consolidated statement, False if Standalone."""
        t_lower = text.lower()
        if "standalone" in t_lower or "separate financial" in t_lower:
            return False
        return True  # Default to Consolidated

    @staticmethod
    def detect_fiscal_year(text: str) -> int:
        """Extract fiscal year integer (e.g. 2026, 2025, 2024)."""
        # Look for e.g. FY 2025-26, FY26, 2026, 2025
        fy_match = re.search(r"202[0-9]-[0-9]{2}", text)
        if fy_match:
            # e.g. 2025-26 -> fiscal year 2026
            year_part = fy_match.group(0).split("-")[0]
            return int(year_part) + 1

        year_match = re.search(r"\b(20[2-3][0-9])\b", text)
        if year_match:
            return int(year_match.group(1))

        return 2025  # Default baseline

    @staticmethod
    def match_canonical_metric(raw_label: str) -> Optional[str]:
        """Map raw line item label to canonical metric taxonomy name."""
        if not raw_label:
            return None

        raw_lowered = raw_label.lower().strip()
        # Direct exact match on raw lowercased
        if raw_lowered in CANONICAL_METRIC_MAP:
            return CANONICAL_METRIC_MAP[raw_lowered]

        # Normalize hyphens and underscores to spaces, strip numbers and punctuation
        normalized = raw_lowered.replace("-", " ").replace("_", " ")
        clean = re.sub(r"[\d\.\(\)\*\:\,]", "", normalized)
        clean = re.sub(r"\s+", " ", clean).strip()

        if clean in CANONICAL_METRIC_MAP:
            return CANONICAL_METRIC_MAP[clean]

        # Substring matching against canonical dictionary
        for key, canonical in CANONICAL_METRIC_MAP.items():
            if key == clean or key in clean or clean in key:
                return canonical

        return None

