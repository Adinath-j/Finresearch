"""Test suite for Structure-Aware and Token-Aware Chunker."""

import unittest
from app.infrastructure.document_processing.chunker import (
    StructureAwareChunker,
    estimate_tokens,
)
from app.infrastructure.document_processing.parser import ParsedPage


class TestStructureAwareChunker(unittest.TestCase):
    """Unit tests for token-aware chunking and metadata preservation."""

    def setUp(self):
        self.chunker = StructureAwareChunker(target_tokens=50, overlap_tokens=10)

    def test_estimate_tokens(self):
        text = "Revenue grew by 15 percent year over year."
        tokens = estimate_tokens(text)
        self.assertGreater(tokens, 0)
        self.assertEqual(tokens, len(text) // 4)

    def test_chunking_preserves_metadata(self):
        sample_page = ParsedPage(
            page_number=3,
            text="Operating profit increased by 12 percent due to automation and cost controls.",
            tables=[],
            section="Management Discussion",
        )
        chunks = self.chunker.chunk_pages(
            pages=[sample_page],
            document_id="doc-123",
            filename="annual_report.pdf",
        )

        self.assertGreaterEqual(len(chunks), 1)
        first_chunk = chunks[0]
        self.assertEqual(first_chunk["document_id"], "doc-123")
        self.assertEqual(first_chunk["filename"], "annual_report.pdf")
        self.assertEqual(first_chunk["page_number"], 3)
        self.assertEqual(first_chunk["page_chunk_index"], 1)
        self.assertEqual(first_chunk["section"], "Management Discussion")
        self.assertFalse(first_chunk["is_table"])
        self.assertIn("Operating profit", first_chunk["text"])

    def test_chunking_handles_tables(self):
        table_page = ParsedPage(
            page_number=7,
            text="Summary statement table below:",
            tables=[{
                "table_index": 1,
                "markdown": "| Revenue | Net Profit |\n| --- | --- |\n| 1000 | 200 |",
            }],
            section="Financial Statements",
        )
        chunks = self.chunker.chunk_pages(
            pages=[table_page],
            document_id="doc-456",
            filename="results.pdf",
        )

        table_chunks = [c for c in chunks if c["is_table"]]
        self.assertEqual(len(table_chunks), 1)
        self.assertEqual(table_chunks[0]["page_number"], 7)
        self.assertIn("Financial Table", table_chunks[0]["text"])
        self.assertIn("| Revenue | Net Profit |", table_chunks[0]["text"])


if __name__ == "__main__":
    unittest.main()

