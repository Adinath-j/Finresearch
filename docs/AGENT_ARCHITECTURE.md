# Multi-Agent Architecture Specifications
**Infosys Springboard — Vidzai Digital**  
**Specialized Agent Roles, Communication Contracts & Orchestration**

---

## 1. Multi-Agent System Overview

The system employs six autonomous, specialized AI agents working cooperatively to deliver end-to-end financial analysis with strict source grounding.

```
+-----------------------------------------------------------------------------------+
|                        LangGraph Shared Typed State                               |
| (workspace_id, session_id, documents, metrics, red_flags, comparisons, reports)   |
+-----------------------------------------------------------------------------------+
       |                    |                    |                   |
+-----------------+  +-----------------+  +-----------------+  +-----------------+
| 1. Document     |  | 2. Extraction   |  | 3. Red Flag     |  | 4. Comparison   |
|    Agent        |  |    Agent        |  |    Agent        |  |    Agent        |
| (Milestone 1)   |  | (Milestone 2)   |  | (Milestone 2)   |  |  (Milestone 3)  |
+-----------------+  +-----------------+  +-----------------+  +-----------------+
                           |                                         |
                     +-----------------+                       +-----------------+
                     | 5. Research     |                       | 6. Report       |
                     |    Agent        |                       |    Agent        |
                     | (Milestone 3)   |                       | (Milestone 3)   |
                     +-----------------+                       +-----------------+
```

---

## 2. Agent Responsibilities & Contracts

### 1. Document Intelligence Agent (*Milestone 1 — Implemented*)
- **Objective**: Ingest, validate, parse, chunk, embed, index, and retrieve financial document passages.
- **Inputs**: Raw PDF binary stream or file path, metadata (workspace ID, session ID, filename).
- **Core Operations**:
  - SHA-256 duplicate detection.
  - Page-by-page text extraction and financial table extraction (`pymupdf` + `find_tables`).
  - Token-aware, structure-aware semantic chunking with page number and section retention.
  - Embedding generation using `sentence-transformers/all-MiniLM-L6-v2` (384-d).
  - Indexing in Qdrant Vector DB with metadata payload.
  - Semantic similarity search with metadata filtering and distance scores.
- **Outputs**: Indexed document record, chunk count, text and table preview, searchable vector collection.

---

### 2. Financial Extraction Agent (*Milestone 2 — Design*)
- **Objective**: Extract standardized financial metrics across statements with strict source citations.
- **Inputs**: Target document ID, statement types (Income Statement, Balance Sheet, Cash Flow).
- **Target Financial Metrics**:
  - *Income Statement*: Revenue, COGS, Gross Profit, Operating Expenses, Operating Income (EBIT), Net Income, Diluted EPS.
  - *Balance Sheet*: Total Assets, Current Assets, Total Liabilities, Current Liabilities, Total Debt, Shareholders' Equity.
  - *Cash Flow*: Cash from Operating Activities, Investing Cash Flow, Financing Cash Flow, Capex, Free Cash Flow.
  - *Financial Indicators*: Revenue Growth, Gross Margin, Operating Margin, Net Margin, Current Ratio, Debt-to-Equity Ratio, Return on Equity.
- **Guiding Constraints**:
  - Distinguish between consolidated and standalone financials.
  - Never fabricate missing figures; distinguish `None` (unavailable) from `0.0`.
  - Perform all ratio computations using Python `Decimal`.
  - Every extracted metric must carry `{document_id, page_number, raw_table_context, is_calculated}`.
- **Output Schema**: Pydantic `ExtractedFinancials` model with validated citations.

---

### 3. Red Flag & Risk Detection Agent (*Milestone 2 — Design*)
- **Objective**: Identify structural financial risks, deterioration, and accounting anomalies using a hybrid rule-based and LLM approach.
- **Inputs**: `ExtractedFinancials` from Extraction Agent + relevant text passages from Document Agent.
- **Hybrid Detection Methodology**:
  - **Rule-Based Engine (Deterministic)**:
    - Increasing leverage: Debt-to-Equity growth > 25% YoY.
    - Deteriorating liquidity: Current Ratio < 1.0 or falling > 20%.
    - Profitability erosion: Consecutive quarterly or annual operating margin drop.
    - Cash conversion anomaly: Operating Cash Flow significantly trailing Net Income.
    - Negative working capital trends.
  - **LLM-Based Analysis (Contextual)**:
    - Auditor qualification or emphasis of matter paragraphs.
    - Going-concern uncertainties.
    - Significant contingent liabilities and pending litigation.
    - Related-party transactions and revenue recognition policy modifications.
    - Management Discussion & Analysis (MD&A) risk factor disclosures.
- **Output Schema**: List of `RedFlagFinding` objects containing:
  `{category, severity (LOW/MEDIUM/HIGH/CRITICAL), title, description, evidence_quote, source_page, period}`.

---

### 4. Cross-Company Comparison Agent (*Milestone 3 — Design*)
- **Objective**: Perform comparative horizontal and vertical financial benchmarking across two or more corporate entities.
- **Inputs**: List of `ExtractedFinancials` across multiple documents/companies and target reporting periods.
- **Core Operations**:
  - Normalize currencies (e.g., INR to USD, EUR to USD using deterministic reference rates).
  - Align reporting periods (e.g., FY25 vs FY25, LTM vs LTM).
  - Check consolidated vs standalone alignment.
  - Compute comparative variances: Percentage differences, compound growth rates, margin spreads.
- **Output Schema**: `ComparisonAnalysisResult` featuring structured matrix and narrative variance drivers.

---

### 5. Financial Research Agent (*Milestone 3 — Design*)
- **Objective**: Answer complex, multi-part qualitative and quantitative financial research questions.
- **Inputs**: User natural-language research query, session context, active document IDs.
- **Core Operations**:
  - Query decomposition: Split multi-part questions into targeted sub-queries.
  - Semantic + lexical hybrid retrieval over Qdrant collections.
  - Evidence synthesis: Ground every factual assertion in retrieved source passages.
  - Explicit insufficiency handling: Explicitly report when the source corpus lacks sufficient evidence.
- **Output Schema**: `ResearchAnswer` containing `{direct_answer, supporting_evidence, citations: [{doc_id, page, quote}], limitations}`.

---

### 6. Report Generation Agent (*Milestone 3 — Design*)
- **Objective**: Compile validated multi-agent findings into a structured, analyst-grade research report.
- **Inputs**: Extracted financials, red flag findings, comparative analysis, and research findings.
- **Report Sections**:
  1. Executive Summary & Investment Thesis.
  2. Company Overview & Business Segments.
  3. Key Financial Highlights & Metrics Table.
  4. Detailed Performance Analysis (Income, Balance Sheet, Cash Flow).
  5. Red Flag & Forensic Risk Assessment.
  6. Peer Comparison & Benchmarking.
  7. Forward-Looking Outlook & Management Guidance.
  8. Sources, Citations & Document Audit Trail.
- **Output Schema**: Structured `FinancialReport` model exportable to JSON, Markdown, and downstream PDF rendering engines.

---

## 3. LangGraph Shared State Model (Preview for Milestone 2)

```python
from typing import Annotated, Dict, List, Optional
from pydantic import BaseModel, Field

class FinancialResearchState(BaseModel):
    workspace_id: str
    session_id: str
    document_ids: List[str] = Field(default_factory=list)
    query: Optional[str] = None
    
    # Document Agent Output
    retrieved_chunks: List[Dict] = Field(default_factory=list)
    
    # Extraction Agent Output
    extracted_metrics: Dict[str, Dict] = Field(default_factory=dict)
    
    # Red Flag Agent Output
    red_flag_findings: List[Dict] = Field(default_factory=list)
    
    # Comparison Agent Output
    comparison_results: Optional[Dict] = None
    
    # Research & Report Agent Outputs
    research_answers: List[Dict] = Field(default_factory=list)
    final_report: Optional[Dict] = None
    
    # Execution Tracking
    errors: List[str] = Field(default_factory=list)
    execution_step: str = "INITIALIZED"
```

