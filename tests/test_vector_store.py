"""Test suite for Vector Store operations (Qdrant & ChromaDB)."""

import unittest
from app.infrastructure.document_processing.embedder import generate_embeddings
from app.infrastructure.vector_store import ChromaVectorStore, get_vector_store


class TestVectorStore(unittest.TestCase):
    """Unit tests for vector indexing and similarity retrieval."""

    def setUp(self):
        # Use dedicated test collection
        self.store = ChromaVectorStore(collection_name="test_financial_chunks_unit")

    def test_upsert_and_similarity_search(self):
        chunks = [
            {
                "chunk_id": "test-doc-1-c1",
                "document_id": "test-doc-1",
                "filename": "test_financials.pdf",
                "page_number": 2,
                "page_chunk_index": 1,
                "section": "Financial Results",
                "is_table": False,
                "text": "Total cloud revenue exceeded fifteen billion dollars in 2025.",
            },
            {
                "chunk_id": "test-doc-1-c2",
                "document_id": "test-doc-1",
                "filename": "test_financials.pdf",
                "page_number": 3,
                "page_chunk_index": 1,
                "section": "Auditor Report",
                "is_table": False,
                "text": "The independent auditors issued an unqualified audit opinion.",
            },
        ]
        texts = [c["text"] for c in chunks]
        embeddings = generate_embeddings(texts)

        upserted_count = self.store.upsert_chunks(chunks, embeddings)
        self.assertEqual(upserted_count, 2)

        # Query for cloud revenue
        query = "How much was the cloud revenue?"
        query_emb = generate_embeddings([query])[0]
        results = self.store.search_chunks(query_emb, top_k=2)

        self.assertGreaterEqual(len(results), 1)
        top_match = results[0]
        self.assertIn("cloud revenue", top_match["text"].lower())
        self.assertEqual(top_match["metadata"]["document_id"], "test-doc-1")
        self.assertEqual(top_match["metadata"]["page_number"], 2)
        self.assertLess(top_match["distance"], 1.0)

    def test_vector_count(self):
        count = self.store.count_chunks()
        self.assertGreaterEqual(count, 0)

    def test_qdrant_vector_store_health_probe(self):
        from unittest.mock import MagicMock, patch
        from app.infrastructure.vector_store.qdrant import QdrantVectorStore

        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp

            qdrant = QdrantVectorStore(url="http://mock-qdrant:6333", collection_name="test_col", vector_size=1536)
            self.assertTrue(qdrant.is_healthy())


if __name__ == "__main__":
    unittest.main()

