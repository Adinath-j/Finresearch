# AI Service Integration Interface Specification
**Infosys Springboard — Vidzai Digital: Multi-Agent Financial Research System**  
**Contract Definition Between Main Application Backend & FastAPI AI Service**

---

## 1. System Boundary and Ownership

The Multi-Agent Financial Research System separates the **Main Application Backend** (Web/API platform) from the **FastAPI AI Service**:

```
+-----------------------------------------------------------------------------------+
|                           Main Application Backend                                |
|  - User Authentication (JWT, RBAC)                                                |
|  - Workspaces & User Management                                                   |
|  - Research Session Orchestration & Frontend UI                                   |
|  - Public File Uploads & Presigned URLs                                           |
+-----------------------------------------------------------------------------------+
                                   |
                HTTP REST API / JSON Payloads & Bearer Auth
                                   v
+-----------------------------------------------------------------------------------+
|                             FastAPI AI Service                                    |
|  - PDF Validation & Text/Table Parsing (PyMuPDF & Docling)                        |
|  - Token-Aware Chunking & Semantic Embeddings                                      |
|  - Qdrant Vector Storage & Hybrid Retrieval                                       |
|  - Financial Metric Extraction (Python Decimal)                                   |
|  - Red Flag Risk Detection (Rule Engine + LLM Disclosures)                        |
|  - LangGraph 3-Agent Workflow Orchestration                                       |
+-----------------------------------------------------------------------------------+
```

### Architectural Principles
1. **Foreign Key Decoupling**: The AI service accepts external identifiers (`workspace_id`, `session_id`, `user_id`, `document_id`) provided by the main application backend. It stores and indexes these IDs to associate processing jobs and findings without managing user accounts or workspace CRUD.
2. **Dedicated Table Namespace**: To prevent database conflicts, all AI service database tables are prefixed with `ai_`:
   - `ai_documents`
   - `ai_processing_jobs`
   - `ai_financial_metrics`
   - `ai_metric_evidence`
   - `ai_red_flag_findings`
   - `ai_agent_runs`
3. **Stateless Processing & Idempotency**: Document ingestion checks the SHA-256 fingerprint. Re-submitting an already processed document immediately returns its indexed state without incurring re-embedding costs.

---

## 2. API Endpoints for Backend Integration

### 2.1 Ingest Document via Backend Reference or Binary Upload
- **Route**: `POST /documents/process`
- **Purpose**: Called by the main backend when a user uploads a new filing or triggers analysis on an existing stored file.
- **Request Body (JSON Reference Mode)**:
  ```json
  {
    "document_id": "doc_9a7b2c",
    "workspace_id": "ws_12345",
    "session_id": "sess_67890",
    "user_id": "user_456",
    "filename": "Infosys_Integrated_Annual_Report_2025-26.pdf",
    "storage_path": "uploads/5f0741a54b034afd98feeda9fa31444e.pdf",
    "trigger_extraction": true,
    "trigger_red_flags": true
  }
  ```
- **Direct Upload Mode**: `POST /documents/upload` accepts `multipart/form-data` with optional `workspace_id`, `session_id`, and `user_id` query parameters.
- **Response**:
  ```json
  {
    "job_id": "job_01h8x9",
    "document_id": "doc_9a7b2c",
    "status": "PROCESSING",
    "filename": "Infosys_Integrated_Annual_Report_2025-26.pdf",
    "indexed": false,
    "message": "Document processing initiated through LangGraph workflow."
  }
  ```

### 2.2 Query Ingestion & Processing Status
- **Route**: `GET /documents/{document_id}/status`
- **Response**:
  ```json
  {
    "document_id": "doc_9a7b2c",
    "status": "COMPLETED",
    "total_pages": 383,
    "total_characters": 1309989,
    "chunk_count": 1664,
    "indexed": true,
    "created_at": "2026-10-28T14:09:35Z",
    "stages": {
      "document_agent": "COMPLETED",
      "extraction_agent": "COMPLETED",
      "red_flag_agent": "COMPLETED"
    }
  }
  ```

### 2.3 Retrieve Extracted Financial Metrics
- **Route**: `GET /documents/{document_id}/extraction`
- **Response**:
  ```json
  {
    "document_id": "doc_9a7b2c",
    "company_name": "Infosys Limited",
    "fiscal_year": 2026,
    "reporting_scope": "CONSOLIDATED",
    "currency": "INR",
    "unit": "CRORES",
    "metrics": {
      "revenue": {
        "value": "153670.00",
        "source_label": "Revenue from operations",
        "statement": "INCOME_STATEMENT",
        "source_page": 195,
        "is_calculated": false
      },
      "net_income": {
        "value": "26248.00",
        "source_label": "Profit for the period (Net Profit)",
        "statement": "INCOME_STATEMENT",
        "source_page": 195,
        "is_calculated": false
      },
      "net_profit_margin": {
        "value": "17.08",
        "statement": "KEY_RATIOS",
        "is_calculated": true,
        "formula": "(net_income / revenue) * 100"
      }
    }
  }
  ```

### 2.4 Retrieve Red Flag Risk Findings
- **Route**: `GET /documents/{document_id}/red-flags`
- **Response**:
  ```json
  {
    "document_id": "doc_9a7b2c",
    "total_findings": 2,
    "findings": [
      {
        "finding_id": "rf_01",
        "category": "DEBT_AND_LEVERAGE",
        "severity": "MEDIUM",
        "title": "Short-Term Debt Increase",
        "description": "Short-term debt grew by 18.5% YoY while cash reserves remained flat.",
        "detection_method": "RULE_BASED",
        "source_page": 194,
        "supporting_evidence": "Note 18: Borrowings increased from INR 1,200 Cr to INR 1,422 Cr..."
      }
    ]
  }
  ```

### 2.5 Semantic Search with Verifiable Citations
- **Route**: `POST /search`
- **Request Body**:
  ```json
  {
    "query": "What are the key risks highlighted by the statutory auditor regarding revenue recognition?",
    "top_k": 5,
    "document_id": "doc_9a7b2c",
    "session_id": "sess_67890",
    "filter_tables_only": false
  }
  ```
- **Response**:
  ```json
  {
    "query": "What are the key risks highlighted by the statutory auditor regarding revenue recognition?",
    "result_count": 1,
    "results": [
      {
        "chunk_id": "doc_9a7b2c-197",
        "text": "Key Audit Matter: Revenue recognition for fixed price contracts involving percentage of completion method...",
        "metadata": {
          "document_id": "doc_9a7b2c",
          "filename": "Infosys_Integrated_Annual_Report_2025-26.pdf",
          "page_number": 197,
          "is_table": false,
          "section": "Auditor Report"
        },
        "distance": 0.2841,
        "score": 0.7159
      }
    ]
  }
  ```

