"""Verify ingestion and multi-document retrieval across seed company documents."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.agents.document_agent import DocumentAgentService
from app.infrastructure.database import get_database_repository
from app.infrastructure.vector_store import get_vector_store


def main():
    service = DocumentAgentService()
    print("Ingesting preloaded seed documents...")
    results = service.ingest_seed_documents()

    print("\n--- Seed Documents Ingestion Results ---")
    for r in results:
        print(f"File: {r.filename:<42} | Status: {r.status} | Pages: {r.pages:<2} | Chunks: {r.chunks:<3} | ID: {r.document_id}")

    # Test cross-company queries
    test_queries = [
        "What was Zenith Energy operating cash flow and capital expenditure?",
        "What is Apex Financial capital to risk assets ratio (CRAR Basel III)?",
        "What are Acme Cloud Technologies subscription revenue and gross profit?",
    ]

    print("\n--- Multi-Document Semantic Retrieval Verification ---")
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        res = service.search(query=q, top_k=2)
        print(f"Matches found: {res.result_count}")
        for match in res.results:
            fname = match.metadata.get("filename")
            page = match.metadata.get("page_number")
            print(f" -> [{fname}, Page {page}] (Distance: {match.distance:.4f}):")
            print(f"    \"{match.text[:140].strip()}...\"")


if __name__ == "__main__":
    main()
