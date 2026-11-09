"""End-to-End Test Suite for Document Agent Service."""

import unittest
from pathlib import Path

from app.agents.document_agent import DocumentAgentService
from app.infrastructure.database import get_database_repository
from app.infrastructure.vector_store import get_vector_store


class TestDocumentAgentEndToEnd(unittest.TestCase):
    """Integration and End-to-End tests using real financial PDF documents."""

    def setUp(self):
        self.service = DocumentAgentService()
        self.seed_file = Path("seed_documents/zenith_energy_earnings_call_q4_fy25.pdf")
        if not self.seed_file.exists():
            from app.infrastructure.document_processing.seed_generator import generate_seed_pdf_files
            generate_seed_pdf_files(Path("seed_documents"))

    def test_end_to_end_ingestion_and_search(self):
        if not self.seed_file.exists():
            self.skipTest("Seed document zenith_energy_earnings_call_q4_fy25.pdf not found.")

        file_bytes = self.seed_file.read_bytes()

        # 1. Ingest PDF
        upload_resp = self.service.process_pdf_upload(
            file_bytes=file_bytes,
            filename=self.seed_file.name,
            workspace_id="default-workspace",
        )

        self.assertIsNotNone(upload_resp.document_id)
        self.assertTrue(upload_resp.stored)
        self.assertTrue(upload_resp.indexed)
        self.assertGreater(upload_resp.total_pages, 0)
        self.assertGreater(upload_resp.chunk_count, 0)

        # 2. Duplicate Detection Idempotency
        second_resp = self.service.process_pdf_upload(
            file_bytes=file_bytes,
            filename=self.seed_file.name,
        )
        self.assertEqual(second_resp.document_id, upload_resp.document_id)
        self.assertTrue(second_resp.already_exists)
        self.assertIn("already exists", second_resp.message)

        # 3. Semantic Search with Evidence Grounding
        query = "What was Zenith Energy total revenue and free cash flow?"
        search_resp = self.service.search(
            query=query,
            top_k=3,
            document_id=upload_resp.document_id,
        )

        self.assertGreaterEqual(search_resp.result_count, 1)
        top_match = search_resp.results[0]
        self.assertEqual(top_match.metadata["document_id"], upload_resp.document_id)
        self.assertEqual(top_match.metadata["page_number"], 1)
        self.assertIn("revenue", top_match.text.lower())
        self.assertLess(top_match.distance, 1.0)

        # 4. Document Summary Verification
        summary = self.service.get_document_summary(upload_resp.document_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary.filename, self.seed_file.name)
        self.assertTrue(summary.indexed)
        self.assertEqual(summary.chunk_count, upload_resp.chunk_count)


if __name__ == "__main__":
    unittest.main()

