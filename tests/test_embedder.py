"""Test suite for Embeddings Engine (OpenAI and SentenceTransformers providers)."""

import math
import unittest
from unittest.mock import MagicMock, patch

from app.infrastructure.document_processing.embedder import (
    OpenAIEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    generate_embeddings,
    get_embedding_dimension,
)


class TestEmbeddingEngine(unittest.TestCase):
    """Unit tests for embedding generation across local and cloud providers."""

    def test_sentence_transformer_provider_dimension_and_encoding(self):
        local_provider = SentenceTransformerEmbeddingProvider()
        self.assertEqual(local_provider.get_dimension(), 384)

        texts = [
            "Infosys reported steady revenue growth in digital transformation services.",
            "Operating cash flow reached record highs in fiscal year 2026.",
        ]
        embeddings = local_provider.generate_embeddings(texts)
        self.assertEqual(len(embeddings), 2)
        self.assertEqual(len(embeddings[0]), 384)
        self.assertEqual(len(embeddings[1]), 384)

        # Verify unit normalization (L2 norm should be approximately 1.0)
        norm = math.sqrt(sum(x * x for x in embeddings[0]))
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_empty_input_returns_empty_list(self):
        local_provider = SentenceTransformerEmbeddingProvider()
        embeddings = local_provider.generate_embeddings([])
        self.assertEqual(embeddings, [])

    def test_openai_embedding_provider_requires_key(self):
        with self.assertRaises(ValueError):
            OpenAIEmbeddingProvider(api_key="")

    @patch("httpx.Client.post")
    def test_openai_embedding_provider_mock_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"embedding": [0.05] * 1536, "index": 0},
                {"embedding": [0.10] * 1536, "index": 1},
            ]
        }
        mock_post.return_value = mock_resp

        openai_prov = OpenAIEmbeddingProvider(api_key="test-sk-key-12345")
        self.assertEqual(openai_prov.get_dimension(), 1536)

        results = openai_prov.generate_embeddings(["Sample chunk 1", "Sample chunk 2"])
        self.assertEqual(len(results), 2)
        self.assertEqual(len(results[0]), 1536)


if __name__ == "__main__":
    unittest.main()
