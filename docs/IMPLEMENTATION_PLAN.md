# Implementation Plan: Milestone 1 Execution
**Infosys Springboard — Vidzai Digital**  
**Document Agent, Workspace Persistence, Vector Abstraction & Test Suite**

---

## 1. Repository Audit Summary

### Completed Features (Found in Existing Codebase)
- Basic FastAPI application (`main.py`) with `/`, `/health`, `/search`, and `/documents/upload`.
- File validation (PDF format check, empty file check, 22MB size limit).
- SHA-256 duplicate detection logic in SQLite (`documents.db`).
- Basic page-level text extraction via PyMuPDF (`page.get_text("text")`).
- Character-based chunking in `chunker.py` (`chunk_size=1000`, `overlap=150`).
- Embeddings generation with `sentence-transformers/all-MiniLM-L6-v2` in `embedder.py`.
- ChromaDB vector persistence in `vector_store.py` (`financial_chunks` collection).
- Real 383-page Infosys Integrated Annual Report FY25-26 preloaded in `uploads/`.

### Gaps & Technical Debt to Address in Milestone 1
- **No Workspaces or Research Sessions**: No database entities or API routes to support named research sessions or document-to-session association.
- **Table Extraction Missing**: Current PyMuPDF extraction only reads raw unstructured text, flattening financial tables into unaligned string sequences.
- **Chunking Lacks Token Awareness**: Chunks are purely character-based and can overflow MiniLM's 512-token limit or split financial tables across boundaries.
- **No Vector DB Abstraction**: Code is tightly coupled to ChromaDB directly. Qdrant vector database is required with clean fallback and configurable endpoints.
- **Database Coupling**: Direct SQLite queries embedded in route handlers rather than a repository abstraction. No Supabase PostgreSQL schema/client.
- **Configuration Hardcoding**: Model names and collection names are hardcoded instead of using environment-based settings.
- **Missing Test Suite**: `test_embedder.py` and `test_vector_store.py` were mentioned in README but do not exist on disk.

---

## 2. Milestone 1 Implementation Roadmap

```mermaid
flowchart LR
    Step1["Step 1: Configuration & Schemas"] --> Step2["Step 2: Database Layer (Postgres + SQLite)"]
    Step2 --> Step3["Step 3: Storage Layer (Local + Supabase)"]
    Step3 --> Step4["Step 4: Vector Store Layer (Qdrant + Chroma)"]
    Step4 --> Step5["Step 5: Document Processing (Tables + Chunker)"]
    Step5 --> Step6["Step 6: Document Agent Service & Workspaces"]
    Step6 --> Step7["Step 7: Seed Documents Preparation"]
    Step7 --> Step8["Step 8: FastAPI Routes Integration"]
    Step8 --> Step9["Step 9: Comprehensive Test Suite & Verification"]
```

### Step 1: Configuration & Schemas (`app/config.py`, `app/schemas/`)
- Create centralized `Settings` class using `pydantic-settings` to manage:
  - `APP_ENV`, `DEBUG`, `PORT`
  - `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`
  - `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`
  - `EMBEDDING_MODEL_NAME`, `EMBEDDING_DIMENSION`
  - `MAX_UPLOAD_SIZE_MB`, `UPLOAD_DIR`, `SEED_DOCS_DIR`
- Define Pydantic schemas for Workspaces, Sessions, Documents, Chunks, and Search.

### Step 2: Database Layer (`app/infrastructure/database/`)
- Define relational models for Workspaces, Sessions, Documents, Chunks, and SessionDocuments.
- Implement dual-mode repository:
  - Supabase PostgreSQL client (SQLAlchemy ORM / DDL for production).
  - Robust SQLite repository (`documents.db`) for immediate, dependency-free local development and testing.

### Step 3: Storage Layer (`app/infrastructure/storage/`)
- Implement `FileStorageInterface`.
- Implement `LocalStorage` (saving to `uploads/` with SHA-256 deduplication).
- Implement `SupabaseStorage` interface stub ready for credentials.

### Step 4: Vector Store Layer (`app/infrastructure/vector_store/`)
- Define `VectorStoreInterface` (`upsert_chunks`, `search_chunks`, `count_chunks`, `delete_document`).
- Implement `QdrantVectorStore` using lightweight HTTP REST client (`httpx`).
- Implement `ChromaVectorStore` wrapping ChromaDB PersistentClient to preserve existing indexes and provide zero-setup local storage.
- Implement `VectorStoreFactory` to automatically instantiate the active provider.

### Step 5: Document Processing (`app/infrastructure/document_processing/`)
- Implement `PyMuPDFParser`:
  - Page-by-page text extraction.
  - Table extraction using `page.find_tables()` and markdown table conversion.
  - Markdown layout rendering via `pymupdf4llm`.
- Implement token-aware `StructureAwareChunker`:
  - Targets ~350-400 tokens with whitespace and sentence snapping.
  - Preserves table integrity and injects metadata tags (`is_table`, `section`, `page_number`).
- Embedder singleton with model dimensions verification and dynamic loading.

### Step 6: Document Agent Service & Workspaces (`app/agents/document_agent/`)
- Implement `DocumentAgentService`:
  - Full ingestion pipeline: upload validation -> SHA-256 check -> parsing -> chunking -> embedding -> indexing -> database persistence.
  - Workspace and session lifecycle management.
  - Document-to-session association.
  - Retrieval and search with filtering.

### Step 7: Seed Documents Preparation (`seed_documents/`)
- Create 3–4 realistic multi-company financial documents:
  1. `infosys_fy26_financials.pdf` (excerpt of key statements from the 383-page report).
  2. `acme_tech_10k_fy25.pdf` (simulated SEC 10-K filing with GAAP balance sheet and income statement).
  3. `apex_financial_annual_report_fy25.pdf` (financial services annual report with loan book and capital ratios).
  4. `zenith_energy_earnings_call_q4_fy25.pdf` (earnings call transcript with management guidance).

### Step 8: FastAPI Routes Integration (`app/api/`, `main.py`)
- Wire up modular routers:
  - `GET /health` (detailed health of DB, vector store, embedder)
  - `POST /workspaces`, `GET /workspaces`
  - `POST /workspaces/{id}/sessions`, `GET /workspaces/{id}/sessions`
  - `POST /sessions/{id}/documents/upload`
  - `POST /documents/upload` (backward compatible)
  - `POST /documents/seed` (trigger ingestion of seed documents)
  - `POST /search` (semantic search with session & document filtering)
  - `GET /documents/{id}`

### Step 9: Testing & Quality Assurance (`tests/`)
- Create test suite covering:
  - PDF validation and error handling.
  - Text and table extraction accuracy.
  - Token-aware chunking and metadata preservation.
  - Embedding dimensions and normalization.
  - Vector upsert and semantic retrieval.
  - Duplicate upload idempotency.
  - Workspace and session management.
  - End-to-end ingestion and search over real financial documents.

