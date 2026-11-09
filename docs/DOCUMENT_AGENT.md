# Document Intelligence Agent Specification
**Infosys Springboard — Vidzai Digital: Multi-Agent Financial Research System**  
**Milestone 1 Implementation & Operational Design**

---

## 1. Role and Core Purpose

The **Document Intelligence Agent** is the foundational ingestion and retrieval engine of the multi-agent system. Its purpose is to transform messy, multi-page financial PDF filings into high-quality, structured, and searchable representations without hallucinating or losing provenance.

### Core Responsibilities
1. **File Validation & Safety**: Verifies file extension, non-empty byte streams, and enforces size thresholds (up to 22 MB default).
2. **Idempotency & SHA-256 Deduplication**: Generates deterministic SHA-256 digests. If a document has already been indexed, it prevents redundant OCR, parsing, embedding, and database writes.
3. **Dual-Engine Layout Parsing**:
   - Primary: PyMuPDF 2.0 with built-in `page.find_tables()` for tabular recognition.
   - Secondary: Docling adapter interface for layout analysis and OCR fallback.
4. **Structure-Aware & Token-Aware Chunking**: Chunks narrative text to ~350 tokens (optimal for Sentence Transformers' 512 positional window) while isolating financial tables as self-contained tabular Markdown units.
5. **Dense Vector Embeddings**: Encodes chunks into 384-dimensional cosine-normalized vectors using `sentence-transformers/all-MiniLM-L6-v2`.
6. **Dual Vector Database Integration**: Upserts vectors and metadata to **Qdrant** (via HTTP REST API), with fallback to local **ChromaDB**.
7. **Semantic Search with Source Citations**: Returns ranked passages accompanied by exact source page numbers and document IDs.

---

## 2. Component Pipeline

```
Raw PDF File / Upload Stream
            |
            v
  [1. Input Validation]  (MIME type, Size <= 22MB, Empty Check)
            |
            v
  [2. SHA-256 Checksum]  <--> Database Check
            |                 (If already indexed -> return summary)
            v
  [3. PyMuPDF Parser]
       ├── Text Extraction (Page-by-page)
       └── Table Detection (`find_tables()` -> Markdown Table formatting)
            |
            v
  [4. Structure-Aware Chunker]
       ├── Tabular Chunks (Preserved intact with headers)
       └── Narrative Chunks (~350 tokens, sentence-snapped)
            |
            v
  [5. Embedding Engine] (SentenceTransformer: all-MiniLM-L6-v2, 384 dims)
            |
            v
  [6. Vector Persistence] (Qdrant REST / ChromaDB fallback)
            |
            v
  [7. Document Registry] (Update `ai_documents` with indexed=1, chunk_count)
```

---

## 3. Data Contracts & Schemas

### Chunk Payload Schema
Every indexed chunk in Qdrant/ChromaDB carries the following payload:

```json
{
  "chunk_id": "doc_001-42",
  "document_id": "doc_001",
  "filename": "annual_report.pdf",
  "page_number": 195,
  "page_chunk_index": 2,
  "section": "Consolidated Financial Statements",
  "is_table": true,
  "token_count": 312,
  "text": "### Financial Table (Page 195)\n| Particulars | FY 2026 | FY 2025 |\n| --- | --- | --- |\n| Revenue from operations | 153,670 | 146,767 |"
}
```

---

## 4. Failure Modes and Recovery

| Failure Scenario | Detection Mechanism | Mitigation Strategy |
|---|---|---|
| **Corrupted PDF** | `pymupdf.open()` raises exception | Returns HTTP 400 with specific corruption error. Document state marked `FAILED`. |
| **Password Protected** | `doc.needs_pass == True` | Rejects upload immediately with explicit notification that encrypted files are unsupported. |
| **Image-Only / Scanned PDF** | Total extracted characters < 100 across document | Marks document status as `NEEDS_OCR` and surfaces actionable message to user. |
| **Qdrant Unreachable** | HTTP connection timeout (1.0s) | Gracefully falls back to local persistent `ChromaDB` without dropping indexing request. |

