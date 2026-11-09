# Red Flag Agent Specification
**Infosys Springboard — Vidzai Digital: Multi-Agent Financial Research System**  
**Milestone 2 Implementation: Hybrid Financial Risk Detection Architecture**

---

## 1. Role and Objective

The **Red Flag Agent** identifies potential financial distress, deteriorating solvency, accounting irregularities, and risk disclosures within analyzed corporate documents.

### Operating Principles
1. **Hybrid Architecture**: Combines **deterministic mathematical rules** (detecting ratio anomalies) with **LLM semantic disclosure analysis** (detecting auditor qualifications and legal risks).
2. **Context-Aware Classification**: Distinguishes between normal cyclical variations and severe anomalies. It surfaces findings as *"potential risk indicators requiring analyst review"*, never as unsubstantiated fraud allegations.
3. **Mandatory Evidence Grounding**: Every finding must cite the exact source document ID, page number, and supporting text or financial metric calculation.
4. **Configurable Thresholds**: Avoids hardcoded, rigid criteria by externalizing threshold parameters into configuration.

---

## 2. Detection Engine Architecture

```
Extracted Financial Metrics (Extraction Agent) + Document Passage Chunks
                                |
                                v
               +---------------------------------+
               |     Red Flag Risk Engine        |
               +----------------+----------------+
                                |
       +------------------------+------------------------+
       |                                                 |
       v                                                 v
[Engine 1: Deterministic Rules]             [Engine 2: LLM Disclosure Analysis]
- Increasing Debt Level                     - Statutory Auditor Qualification
- Negative / Declining Operating Cash Flow   - Going-Concern Uncertainty Warnings
- Profitability & Margin Deterioration       - Material Accounting Policy Changes
- Liquidity Deterioration (Current Ratio)   - Significant Contingent Liabilities
- Cash Flow Trailing Net Income              - Key Audit Matters (KAM) Anomalies
       |                                                 |
       +------------------------+------------------------+
                                |
                                v
               [Evidence Validation & Deduplication]
               Binds Page Citations, Assigns Severity (LOW/MEDIUM/HIGH/CRITICAL)
                                |
                                v
               Structured Red Flag Findings Output
```

---

## 3. Supported Risk Rules (Deterministic Engine)

### 3.1 Debt & Leverage Risk (`DEBT_AND_LEVERAGE`)
- **Rule 1.1**: *Total Debt Growth > 25% YoY* while Operating Income is flat or declining.
  - Severity: `HIGH`
  - Formula: `(Total_Debt_t - Total_Debt_t-1) / Total_Debt_t-1 > 0.25`
- **Rule 1.2**: *Debt-to-Equity Ratio > 2.0x* (or > 3.0x for capital-intensive firms).
  - Severity: `MEDIUM` to `HIGH`

### 3.2 Cash Flow & Earnings Quality (`CASH_FLOW_DIVERGENCE`)
- **Rule 2.1**: *Operating Cash Flow is Negative* despite positive reported Net Income.
  - Severity: `HIGH`
  - Rationale: High-risk earnings quality signal indicating aggressive revenue recognition or ballooning uncollected receivables.
- **Rule 2.2**: *Free Cash Flow is Negative for consecutive periods*.
  - Severity: `MEDIUM`

### 3.3 Profitability & Margin Deterioration (`PROFITABILITY_DECLINE`)
- **Rule 3.1**: *Operating Profit Margin drops by more than 300 basis points (3.0%) YoY*.
  - Severity: `MEDIUM`
- **Rule 3.2**: *Net Profit declines > 20% YoY* while Revenue is growing (Margin Compression).
  - Severity: `HIGH`

### 3.4 Liquidity & Solvency Deterioration (`LIQUIDITY_DETERIORATION`)
- **Rule 4.1**: *Current Ratio < 1.0x*.
  - Severity: `HIGH`
  - Rationale: Current liabilities exceed liquid assets, presenting near-term working capital risk.
- **Rule 4.2**: *Current Ratio drops by > 20% YoY*.
  - Severity: `MEDIUM`

---

## 4. Narrative Disclosure Analysis (LLM Engine)

The LLM inspects retrieved text passages from the Auditor's Report, Notes to Accounts, and MD&A:
1. **Auditor Qualifications & Disclaimers**: Detects phrases like *"except for the effects of"*, *"disclaimer of opinion"*, *"emphasis of matter regarding recoverability"*.
2. **Going Concern Disclosures**: Identifies statements indicating *"substantial doubt about the company's ability to continue as a going concern"*.
3. **Contingent Liabilities & Tax Disputes**: Identifies material tax demands or pending legal proceedings that exceed 10% of net worth.
4. **Key Audit Matters (KAMs)**: Analyzes whether KAMs describe high estimation uncertainty, asset impairment, or goodwill write-downs.

---

## 5. Output Schema

```python
class RedFlagFinding(BaseModel):
    finding_id: str
    category: RiskCategory             # DEBT_AND_LEVERAGE, CASH_FLOW_DIVERGENCE, etc.
    severity: RiskSeverity             # LOW, MEDIUM, HIGH, CRITICAL
    title: str                         # Concise finding headline
    description: str                   # Detailed analysis of the risk
    supporting_evidence: str           # Source text quote or mathematical proof
    reason_for_classification: str     # Rule trigger explanation or LLM disclosure context
    relevant_period: str               # e.g., "FY 2025-26"
    source_citation: SourceCitation    # Page number, document ID, exact quote
```

