"""Standalone component check for vector storage and retrieval."""

import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from embedder import generate_embeddings
from vector_store import TEST_COLLECTION_NAME, count_chunks, search_chunks, upsert_chunks


def main():
    print(f"Testing vector storage with collection: {TEST_COLLECTION_NAME}...")

    chunks = [
        {
            "chunk_id": "test-chunk-1",
            "document_id": "doc-test-001",
            "filename": "sample_report.pdf",
            "page_number": 1,
            "page_chunk_index": 1,
            "text": "Infosys revenue growth was driven by cloud and digital transformation contracts.",
        },
        {
            "chunk_id": "test-chunk-2",
            "document_id": "doc-test-001",
            "filename": "sample_report.pdf",
            "page_number": 2,
            "page_chunk_index": 1,
            "text": "Free cash flow for the year was 2.8 billion dollars, representing 105% of net profit.",
        },
    ]

    texts = [c["text"] for c in chunks]
    embeddings = generate_embeddings(texts)

    upserted = upsert_chunks(chunks, embeddings, collection_name=TEST_COLLECTION_NAME)
    print(f"Upserted {upserted} chunks.")

    query = "What drove revenue growth?"
    results = search_chunks(query, top_k=2, collection_name=TEST_COLLECTION_NAME)

    assert len(results) > 0, "Expected at least one search result."
    print("Top match retrieved:")
    print(f"Text: {results[0]['text']}")
    print(f"Page: {results[0]['metadata'].get('page_number')}")
    print(f"Distance: {results[0].get('distance')}")

    total = count_chunks(TEST_COLLECTION_NAME)
    print(f"Total chunks in test collection: {total}")
    print("Vector store test passed!")


if __name__ == "__main__":
    main()

