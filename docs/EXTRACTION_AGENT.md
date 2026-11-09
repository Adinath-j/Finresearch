# Financial Extraction Agent Specification
**Infosys Springboard — Vidzai Digital: Multi-Agent Financial Research System**  
**Milestone 2 Implementation: Structured Financial Metric Extraction & Arithmetic Engine**

---

## 1. Role and Objective

The **Financial Extraction Agent** automatically extracts standardized financial metrics, indicators, and ratios from parsed corporate documents.

### Key Objectives
1. **Multi-Statement Coverage**: Extracts items from the **Income Statement**, **Balance Sheet**, and **Cash Flow Statement**.
2. **Strict Source Grounding**: Every extracted figure carries a `SourceCitation` referencing `{document_id, filename, page_number, exact_quote, is_calculated}`.
3. **Deterministic Arithmetic**: Ratio calculations (e.g., Gross Margin, Current Ratio, Debt-to-Equity) and Growth Rates are computed using **Python `Decimal`**, never by delegating arithmetic to an LLM.
4. **Accounting Semantics**: Normalizes accounting parentheses `(1,200)` to negative values `-1200`, extracts multiplier units (`Crores`, `Millions`, `Thousands`), and records reporting currency (`INR`, `USD`).
5. **No Hallucinated Numbers**: Distinguishes missing items (`None`) from numerical zero (`0.0`). Missing values are never guessed.

---

## 2. Multi-Stage Extraction Pipeline

```
Parsed Document Chunks & Financial Tables
                   |
                   v
   [Stage 1: Table & Metric Parser]
   Identifies candidate financial statement tables (Income, Balance, Cash Flow)
                   |
                   v
   [Stage 2: Deterministic Normalization]
   - Parses numbers, decimals, commas, and parentheses
   - Detects reporting scope (Consolidated vs Standalone)
   - Resolves units & currency
                   |
                   v
   [Stage 3: LLM Disclosures & Semantic Interpretation]
   - Maps ambiguous company-specific line items to canonical taxonomy
   - Extracts narrative figures from footnotes and MD&A
                   |
                   v
   [Stage 4: Python Decimal Arithmetic Engine]
   - Computes financial ratios and growth rates
   - Records input formulas and calculation basis
                   |
                   v
   [Stage 5: Pydantic Validation & Source Citation Binding]
   Constructs `ExtractedFinancials` model with complete provenance
```

---

## 3. Financial Metrics Taxonomy

### 3.1 Income Statement
- `REVENUE`: Revenue from operations / Total turnover.
- `COGS`: Cost of goods sold / Raw material & direct operating costs.
- `GROSS_PROFIT`: Revenue minus COGS.
- `OPERATING_EXPENSES`: Total SG&A, employee benefits, and general administrative expenses.
- `OPERATING_INCOME`: Operating profit / EBIT.
- `EBITDA`: Operating income before depreciation and amortization.
- `PROFIT_BEFORE_TAX`: Earnings before income tax.
- `NET_INCOME`: Profit for the period after taxes.
- `EPS_DILUTED`: Diluted earnings per share.

### 3.2 Balance Sheet
- `TOTAL_ASSETS`: Sum of current and non-current assets.
- `CURRENT_ASSETS`: Cash, short-term investments, inventories, receivables.
- `NON_CURRENT_ASSETS`: PP&E, intangible assets, long-term investments.
- `TOTAL_LIABILITIES`: Sum of current and long-term liabilities.
- `CURRENT_LIABILITIES`: Accounts payable, short-term debt, current provisions.
- `NON_CURRENT_LIABILITIES`: Long-term borrowings, deferred tax liabilities.
- `TOTAL_DEBT`: Short-term borrowings + Long-term borrowings.
- `SHAREHOLDERS_EQUITY`: Share capital + reserves and surplus.

### 3.3 Cash Flow Statement
- `OPERATING_CASH_FLOW`: Net cash generated from operating activities.
- `INVESTING_CASH_FLOW`: Net cash used in investing activities.
- `FINANCING_CASH_FLOW`: Net cash generated/used in financing activities.
- `CAPITAL_EXPENDITURE`: Purchase of property, plant, equipment (PP&E).
- `FREE_CASH_FLOW`: Calculated deterministically as `Operating Cash Flow - Capital Expenditure`.

### 3.4 Financial Indicators & Calculated Ratios
Calculated deterministically using Python `Decimal`:
- **Gross Margin**: `(Gross Profit / Revenue) * 100`
- **Operating Margin**: `(Operating Income / Revenue) * 100`
- **Net Profit Margin**: `(Net Income / Revenue) * 100`
- **Current Ratio**: `Current Assets / Current Liabilities`
- **Quick Ratio**: `(Cash + Marketable Securities + Receivables) / Current Liabilities`
- **Debt-to-Equity Ratio**: `Total Debt / Shareholders' Equity`
- **Return on Equity (RoE)**: `(Net Income / Shareholders' Equity) * 100`
- **Revenue Growth (YoY)**: `((Current Revenue - Prior Revenue) / Prior Revenue) * 100`

---

## 4. Structured Output Schema

The agent outputs validated Pydantic models:

```python
class ExtractedMetric(BaseModel):
    name: str                           # e.g., "REVENUE"
    value: Decimal                      # e.g., Decimal("153670.00")
    raw_text: str                       # e.g., "153,670"
    currency: str                       # e.g., "INR"
    unit: str                           # e.g., "CRORES"
    fiscal_year: int                    # e.g., 2026
    period: ReportingPeriod             # ANNUAL, QUARTERLY
    is_consolidated: bool               # True if consolidated
    citation: SourceCitation            # Document ID, page number, verbatim quote
    is_calculated: bool                 # False if direct from table, True if derived
    formula: Optional[str] = None       # Calculation equation if is_calculated is True
```

