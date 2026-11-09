# Technology Decisions & Rationale
**Infosys Springboard — Vidzai Digital**  
**Milestone 1 Architectural Choices & Resource Optimization**

---

## 1. Primary Database: Supabase PostgreSQL with SQLite Local Fallback

### Decision
Adopt **Supabase PostgreSQL** as the primary production database with **SQLAlchemy ORM** / **psycopg** driver, coupled with a seamless **SQLite local fallback** (`documents.db`).

### Rationale
- Supabase provides a managed, cloud-native PostgreSQL instance with JSONB support, row-level security, and connection pooling.
- SQLAlchemy provides type-safe ORM models and DDL generation.
- The dual-mode architecture guarantees that developers can run the entire service and automated test suite locally without an active internet connection or external cloud database credentials.

---

## 2. Vector Database: Qdrant with ChromaDB Migration Safety

### Decision
Introduce **Qdrant** as the primary vector search engine (via REST client / cloud / local container), while maintaining an abstraction layer that preserves the existing **ChromaDB** implementation until Qdrant is fully validated.

### Rationale
- **Qdrant Advantages**: Qdrant offers high-performance payload filtering (filtering by `document_id`, `session_id`, `page_number`, `is_table`), native JSON payloads, and horizontal scalability for enterprise financial search.
- **REST Protocol Efficiency**: Using standard HTTP REST via `httpx` allows connecting to Qdrant without heavyweight native binary compilation issues.
- **Migration Safety**: Existing ChromaDB vectors and SQLite records in `chroma_db/` and `documents.db` are preserved so ongoing work is never broken.

---

## 3. Document Parsing: PyMuPDF 2.0 with Financial Table Extraction & Docling Interface

### Decision
Implement `DocumentParserInterface` with `PyMuPDFParser` as the primary production engine utilizing `pymupdf.Page.find_tables()` and `pymupdf4llm`, while providing a pluggable interface for `DoclingParser`.

### Rationale
- PyMuPDF 2.0 is fast, low-memory, and provides built-in table detection through `find_tables()`. It reliably extracts multi-column corporate financial statements into structured markdown tables.
- `pymupdf4llm` automatically preserves structural formatting (headings, markdown bolding, list items) which dramatically improves retrieval chunk coherence.
- The modular parser interface allows dropping in IBM Docling for scanned/complex multi-page graphics without changing the Document Agent business logic.

---

## 4. Embedding Model: Sentence Transformers (`all-MiniLM-L6-v2` Baseline vs BGE)

### Decision
Retain `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional) as the default baseline embedding model, while providing externalized configuration (`EMBEDDING_MODEL_NAME`) to evaluate `BAAI/bge-small-en-v1.5`.

### Rationale
- `all-MiniLM-L6-v2` operates within a modest memory footprint (~120MB VRAM/RAM) and exhibits fast CPU inference (~15ms per chunk), making it optimal for resource-constrained environments.
- Embedding dimensions are tracked dynamically (`embedder.get_embedding_dimension()`) so vector store collection dimensions always match the loaded model.
- Model loading is wrapped in a thread-safe singleton (`@lru_cache(maxsize=1)`) to prevent multiple copies being loaded into memory.

---

## 5. Chunking Strategy: Structure-Aware and Token-Aware Windowing

### Decision
Move from naive character splitting to a structure-aware, token-aware chunker that targets 300–400 tokens per chunk with 50-token overlap, preserving table boundaries and document sections.

### Rationale
- MiniLM models have a hard positional embedding constraint of 512 tokens (optimal at <= 384 tokens). Unchecked character chunking frequently overflows this limit on dense tables or code-like figures.
- Table preservation ensures financial rows and headers are kept intact within the same chunk rather than arbitrarily cut mid-row.

---

## 6. Financial Precision: Python Decimal

### Decision
Mandate Python's standard library `Decimal` for all arithmetic operations (to be implemented in Milestone 2 Extraction Agent).

### Rationale
- Standard IEEE-754 binary floating-point arithmetic (`float`) causes rounding errors (e.g., `0.1 + 0.2 != 0.3`) which are unacceptable in corporate financial audits, share counts, or statutory balance sheet checks.

