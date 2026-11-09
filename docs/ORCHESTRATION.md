# Multi-Agent Orchestration Specification
**Infosys Springboard — Vidzai Digital: Multi-Agent Financial Research System**  
**Milestone 2 Implementation: LangGraph Sequential 3-Agent Workflow**

---

## 1. Orchestration Architecture

The system uses **LangGraph** to coordinate multi-agent execution. In Milestone 2, the pipeline executes the first three specialized agents in a strictly controlled, stateful sequential sequence:

```
[Document Processing Request]
              |
              v
     (Document Agent Node)
              |
              v
     Is Document Indexed?
     ├── [No]  ──> (Failure / Retry Node) ──> Return Error State
     └── [Yes]
              |
              v
    (Extraction Agent Node)
              |
              v
     Is Extraction Valid?
     ├── [No]  ──> (Correction / Partial Retry)
     └── [Yes]
              |
              v
    (Red Flag Agent Node)
              |
              v
  (Evidence Validation Node)
              |
              v
     (Persistence Node) ──> Saves records to `ai_documents`, `ai_financial_metrics`,
              |             `ai_red_flag_findings`, `ai_agent_runs`
              v
     [Workflow Completed]
```

---

## 2. Shared Typed State: `FinancialResearchState`

The state passed across all LangGraph nodes preserves execution context, errors, and agent outputs:

```python
class FinancialResearchState(BaseModel):
    # Context Identifiers
    workspace_id: str
    session_id: str
    user_id: Optional[str] = None
    document_id: str
    filename: str

    # Workflow Control
    current_phase: str = "INITIALIZED"
    is_failed: bool = False
    validation_passed: bool = False
    retry_count: int = 0
    errors: List[str] = Field(default_factory=list)
    execution_steps: List[AgentExecutionLog] = Field(default_factory=list)

    # Document Agent Output
    total_pages: int = 0
    total_characters: int = 0
    chunk_count: int = 0
    is_indexed: bool = False
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)

    # Extraction Agent Output (Milestone 2)
    extracted_financials: Optional[Dict[str, Any]] = None
    extracted_metrics_count: int = 0

    # Red Flag Agent Output (Milestone 2)
    red_flag_findings: List[Dict[str, Any]] = Field(default_factory=list)
    red_flag_count: int = 0

    # Output Summary
    final_summary: Optional[Dict[str, Any]] = None
```

---

## 3. Node Specifications and Conditional Edges

1. **`document_agent_node`**:
   - Ingests PDF bytes or reads stored file path.
   - Extracts text and financial tables; generates chunks and embeddings.
   - Upserts vectors into Qdrant/ChromaDB.
   - Output: Updates `total_pages`, `chunk_count`, `is_indexed=True`.

2. **Conditional Edge: `should_continue_to_extraction`**:
   - If `is_indexed == True`, routes to `extraction_agent_node`.
   - If `is_indexed == False`, routes to `handle_failure_node`.

3. **`extraction_agent_node`**:
   - Analyzes financial tables and text chunks.
   - Extracts Income Statement, Balance Sheet, Cash Flow metrics using Python `Decimal`.
   - Computes financial ratios deterministically.
   - Binds source page citations to every metric.

4. **Conditional Edge: `validate_extraction_results`**:
   - Verifies that at least one core metric (e.g., Revenue or Net Income) was extracted and citations are present.
   - If valid, routes to `red_flag_agent_node`.
   - If invalid, triggers controlled retry or logs partial extraction warning.

5. **`red_flag_agent_node`**:
   - Evaluates deterministic ratio rules against `extracted_financials`.
   - Dispatches LLM disclosure analysis for auditor notes, going-concern warnings, and contingent liabilities.
   - Deduplicates and ranks findings by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).

6. **`evidence_validation_node`**:
   - Validates that every red flag finding has an exact page citation matching the source document.

7. **`persistence_node`**:
   - Atomically records outputs in the database repository:
     - `ai_financial_metrics` & `ai_metric_evidence`
     - `ai_red_flag_findings`
     - `ai_agent_runs` (execution audit log)
   - Updates document processing status to `COMPLETED`.

---

## 4. Resilience and Fallback Execution

The orchestration layer is designed to run robustly in all environments:
- When the `langgraph` package is installed, it runs through the compiled `StateGraph`.
- A resilient Python workflow runner executes the identical node contracts, error routing, and checkpointing even in environments where external graph libraries are not yet installed.

