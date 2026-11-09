"""Document Intelligence Agent Service.

Core implementation for Milestone 1:
- PDF upload and validation
- Duplicate detection via SHA-256
- Text and financial table extraction
- Structure-aware chunking
- Embedding generation
- Qdrant/Chroma vector persistence
- Research workspace and session association
- Semantic document retrieval
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import get_settings
from app.infrastructure.database import (
    DatabaseRepositoryInterface,
    get_database_repository,
)
from app.infrastructure.document_processing import (
    DocumentParserInterface,
    PyMuPDFParser,
    StructureAwareChunker,
    generate_embeddings,
)
from app.infrastructure.storage import FileStorageInterface, get_file_storage
from app.infrastructure.vector_store import (
    VectorStoreInterface,
    get_vector_store,
)
from app.schemas.document import DocumentSummary, DocumentUploadResponse, SeedDocumentResult
from app.schemas.search import SearchResponse, SearchResultItem

logger = logging.getLogger(__name__)


class DocumentAgentService:
    """Production service coordinating document ingestion, indexing, and search."""

    def __init__(
        self,
        repository: Optional[DatabaseRepositoryInterface] = None,
        storage: Optional[FileStorageInterface] = None,
        vector_store: Optional[VectorStoreInterface] = None,
        parser: Optional[DocumentParserInterface] = None,
        chunker: Optional[StructureAwareChunker] = None,
    ):
        self.settings = get_settings()
        self.repo = repository or get_database_repository()
        self.storage = storage or get_file_storage()
        self.vector_store = vector_store or get_vector_store()
        self.parser = parser or PyMuPDFParser()
        self.chunker = chunker or StructureAwareChunker()

    def process_pdf_upload(
        self,
        file_bytes: bytes,
        filename: str,
        workspace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> DocumentUploadResponse:
        """Validate, deduplicate, parse, chunk, embed, and index an uploaded PDF."""
        # 1. Validation
        if not filename or not filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are supported.")

        if not file_bytes:
            raise ValueError("The uploaded file is empty.")

        if len(file_bytes) > self.settings.max_file_size:
            max_mb = self.settings.max_file_size // (1024 * 1024)
            raise ValueError(f"File exceeds the {max_mb} MB limit.")

        # 2. SHA-256 Duplicate Check
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing_doc = self.repo.get_document_by_sha256(file_hash)

        if not document_id and existing_doc and existing_doc.get("indexed") == 1:
            doc_id = existing_doc["document_id"]
            if session_id:
                self.repo.add_document_to_session(session_id, doc_id)

            return DocumentUploadResponse(
                document_id=doc_id,
                filename=filename,
                total_pages=existing_doc.get("total_pages", 0),
                characters_extracted=existing_doc.get("total_characters", 0),
                text_preview="Document already indexed in system.",
                stored=True,
                indexed=True,
                already_exists=True,
                chunk_count=existing_doc.get("chunk_count", 0),
                chunk_preview=[],
                message="This document already exists and is indexed.",
                session_id=session_id,
            )

        # 3. Document ID and File Storage
        document_id = document_id or (existing_doc["document_id"] if existing_doc else uuid4().hex)
        stored_path = self.storage.save_file(file_bytes, filename, document_id)

        # 4. Parse PDF (Text + Tables)
        try:
            parsed_pages = self.parser.parse_pdf(file_bytes)
        except Exception as e:
            logger.error("Failed to parse PDF %s: %s", filename, e)
            raise ValueError(f"Unable to parse PDF: {e}") from e

        total_pages = len(parsed_pages)
        total_tables = sum(len(p.tables) for p in parsed_pages)
        full_text = "\n\n".join(p.text for p in parsed_pages if p.text).strip()
        total_chars = len(full_text)

        # 5. Structure-Aware & Token-Aware Chunking
        chunks = self.chunker.chunk_pages(parsed_pages, document_id, filename)

        # 6. Register initial record before vector storage
        storage_provider = getattr(self.storage, "get_storage_provider", lambda: "local")()
        object_key = getattr(self.storage, "get_object_key", lambda doc_id: f"{doc_id}.pdf")(document_id)
        bucket_name = getattr(self.storage, "bucket_name", None)
        storage_path_val = (
            f"supabase://{bucket_name}/{object_key}"
            if storage_provider == "supabase"
            else str(stored_path)
        )

        doc_record = {
            "document_id": document_id,
            "workspace_id": workspace_id or "default-workspace",
            "sha256": file_hash,
            "filename": filename,
            "stored_filename": object_key,
            "storage_path": storage_path_val,
            "total_pages": total_pages,
            "total_characters": total_chars,
            "chunk_count": len(chunks),
            "indexed": 0,
            "mime_type": "application/pdf",
            "metadata": {
                "tables_detected": total_tables,
                "sections": list({p.section for p in parsed_pages if p.section}),
                "storage_provider": storage_provider,
                "object_key": object_key,
                "bucket": bucket_name,
            },
        }
        self.repo.create_document(doc_record)

        if session_id:
            self.repo.add_document_to_session(session_id, document_id)

        # 7. Embedding Generation & Vector Indexing
        indexed_successfully = False
        if chunks:
            try:
                texts = [c["text"] for c in chunks]
                embeddings = generate_embeddings(texts)
                self.vector_store.upsert_chunks(chunks, embeddings)

                self.repo.update_document_indexed(
                    document_id=document_id,
                    indexed=1,
                    chunk_count=len(chunks),
                    total_pages=total_pages,
                    total_characters=total_chars,
                    metadata=doc_record["metadata"],
                )
                indexed_successfully = True
            except Exception as e:
                logger.exception("Failed to index document %s into vector store: %s", document_id, e)
                raise RuntimeError(f"Document saved, but vector indexing failed: {e}") from e

        # 8. Construct Response Message
        if indexed_successfully:
            msg = f"PDF processed successfully. {total_pages} pages, {total_tables} financial tables, {len(chunks)} chunks indexed."
        elif not full_text:
            msg = "PDF saved, but no selectable text was found. Scanned PDFs may require OCR."
        else:
            msg = "PDF saved, but no chunks were generated. Document is not indexed."

        chunk_previews = [
            {
                "page_number": c["page_number"],
                "is_table": c.get("is_table", False),
                "text": c["text"][:250],
            }
            for c in chunks[:3]
        ]

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            total_pages=total_pages,
            characters_extracted=total_chars,
            text_preview=full_text[:1500],
            stored=True,
            indexed=indexed_successfully,
            already_exists=False,
            chunk_count=len(chunks),
            chunk_preview=chunk_previews,
            message=msg,
            session_id=session_id,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        session_id: Optional[str] = None,
        filter_tables_only: Optional[bool] = None,
    ) -> SearchResponse:
        """Execute semantic search over indexed financial document passages."""
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query string must not be empty.")

        query_emb = generate_embeddings([clean_query])[0]

        filters: Dict[str, Any] = {}
        if document_id:
            filters["document_id"] = document_id
        if filter_tables_only:
            filters["is_table"] = True

        raw_results = self.vector_store.search_chunks(
            query_embedding=query_emb,
            top_k=top_k,
            filters=filters,
        )

        items = [
            SearchResultItem(
                chunk_id=r["chunk_id"],
                text=r["text"],
                metadata=r["metadata"],
                distance=r["distance"],
                score=r.get("score"),
            )
            for r in raw_results
        ]

        # Identify which retriever was active
        retriever_name = type(self.vector_store).__name__

        return SearchResponse(
            query=clean_query,
            result_count=len(items),
            results=items,
            retriever_used=retriever_name,
        )

    def get_document_summary(self, document_id: str) -> Optional[DocumentSummary]:
        """Fetch full document summary from repository."""
        doc = self.repo.get_document_by_id(document_id)
        if not doc:
            return None

        return DocumentSummary(
            document_id=doc["document_id"],
            workspace_id=doc.get("workspace_id"),
            filename=doc["filename"],
            stored_filename=doc["stored_filename"],
            sha256=doc["sha256"],
            total_pages=doc.get("total_pages", 0),
            total_characters=doc.get("total_characters", 0),
            chunk_count=doc.get("chunk_count", 0),
            indexed=bool(doc.get("indexed", 0)),
            created_at=doc["created_at"],
            metadata=doc.get("metadata", {}),
        )

    def ingest_seed_documents(self) -> List[SeedDocumentResult]:
        """Process and index preloaded seed financial documents."""
        seed_dir = Path(self.settings.seed_docs_dir)
        results: List[SeedDocumentResult] = []

        # Ensure seed PDFs exist
        pdf_files = list(seed_dir.glob("*.pdf")) if seed_dir.exists() else []
        if not pdf_files:
            try:
                from app.infrastructure.document_processing.seed_generator import generate_seed_pdf_files
                pdf_files = generate_seed_pdf_files(seed_dir)
            except Exception as e:
                logger.warning("Could not auto-generate seed PDFs: %s", e)

        for pdf_file in sorted(pdf_files):
            try:
                data = pdf_file.read_bytes()
                resp = self.process_pdf_upload(
                    file_bytes=data,
                    filename=pdf_file.name,
                    workspace_id="default-workspace",
                )
                results.append(
                    SeedDocumentResult(
                        filename=pdf_file.name,
                        document_id=resp.document_id,
                        status="Indexed" if resp.indexed else "Failed",
                        pages=resp.total_pages,
                        chunks=resp.chunk_count,
                    )
                )
            except Exception as e:
                logger.error("Error processing seed document %s: %s", pdf_file.name, e)
                results.append(
                    SeedDocumentResult(
                        filename=pdf_file.name,
                        document_id="",
                        status=f"Error: {e}",
                        pages=0,
                        chunks=0,
                    )
                )

        return results

