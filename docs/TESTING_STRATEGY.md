# Testing and Quality Assurance Strategy
**Infosys Springboard — Vidzai Digital: Multi-Agent Financial Research System**  
**Milestone 1 & Milestone 2 Testing Protocol**

---

## 1. Testing Philosophy

In corporate financial intelligence, software reliability is paramount. A faulty formula, floating-point rounding error, or missing page citation can lead to invalid financial analysis.

Our testing protocol enforces four principles:
1. **Zero External Network Dependencies during CI/Unit Testing**: Tests must execute entirely offline using local fixtures and deterministic mock LLM providers.
2. **Deterministic Financial Mathematics**: Ratios and growth rates must be tested against exact known calculations using Python `Decimal`.
3. **Strict Citation Verifiability**: Every test asserts that extracted metrics and red flag findings carry accurate page citations from the source document.
4. **End-to-End Real-Document Ingestion**: End-to-end tests run against real financial reports (e.g., Infosys Annual Report, Acme Cloud SEC 10-K).

---

## 2. Test Suite Hierarchy

```
tests/
├── test_validation.py          # PDF upload format, size limits, empty file rejection
├── test_parser.py              # PyMuPDF text & financial table markdown extraction
├── test_chunker.py             # Structure-aware token windowing & table isolation
├── test_embedder.py            # MiniLM dimensions (384), normalization, offline loading
├── test_vector_store.py        # Vector upsert & semantic similarity search
├── test_database.py            # SQLite & Supabase DDL, duplicate detection by SHA-256
├── test_document_agent.py      # Milestone 1 End-to-end document processing
├── test_extractor.py           # Milestone 2 Extraction Agent statement parsing
├── test_calculations.py        # Python Decimal financial ratio & growth rate correctness
├── test_red_flag_rules.py      # Deterministic risk detection rules (Debt, Cash Flow, Margins)
├── test_red_flag_analyzer.py   # LLM disclosure risk analysis (Auditor, Going-Concern)
├── test_llm_provider.py        # LLM provider interface and mock generation
├── test_orchestration.py       # LangGraph 3-agent sequential workflow execution
└── test_milestone2_e2e.py      # End-to-end multi-agent pipeline on real financial PDF
```

---

## 3. Evaluation Metrics

| Metric | Target | Verification Method |
|---|---|---|
| **Numeric Extraction Accuracy** | > 95% | Compared extracted `Decimal` values against known figures in seed documents. |
| **Arithmetic Correctness** | 100% | Unit tests on margin, ratio, and growth formulas with zero floating-point drift. |
| **Citation Precision** | 100% | Verify that cited page number contains the quoted text in the PDF. |
| **Red Flag Precision** | > 90% | Zero false alarms triggered on pristine financial statements. |
| **Pipeline Idempotency** | 100% | Re-submitting identical SHA-256 hash yields stored records without duplicate embeddings. |
| **Test Execution Speed** | < 10s | Complete 25+ test suite executes quickly on standard developer hardware. |

---

## 4. Execution Commands

Run the complete test suite:
```powershell
python run_tests.py
```

Run individual test modules:
```powershell
python -m unittest tests/test_extractor.py
python -m unittest tests/test_red_flag_rules.py
python -m unittest tests/test_orchestration.py
```

