"""Test suite for PDF validation, empty files, and error handling."""

import unittest
from app.agents.document_agent import DocumentAgentService
from app.infrastructure.database import SQLiteRepository
from app.infrastructure.storage import LocalFileStorage
from app.infrastructure.vector_store import ChromaVectorStore


class TestPDFValidation(unittest.TestCase):
    """Unit tests for PDF input validation rules."""

    def setUp(self):
        self.service = DocumentAgentService()

    def test_reject_non_pdf_extension(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.process_pdf_upload(
                file_bytes=b"sample text",
                filename="statement.xlsx",
            )
        self.assertIn("Only PDF files are supported", str(ctx.exception))

    def test_reject_empty_file(self):
        with self.assertRaises(ValueError) as ctx:
            self.service.process_pdf_upload(
                file_bytes=b"",
                filename="empty.pdf",
            )
        self.assertIn("The uploaded file is empty", str(ctx.exception))

    def test_reject_oversized_file(self):
        oversized = b"0" * (23 * 1024 * 1024)  # 23MB > 22MB limit
        with self.assertRaises(ValueError) as ctx:
            self.service.process_pdf_upload(
                file_bytes=oversized,
                filename="large.pdf",
            )
        self.assertIn("exceeds the 22 MB limit", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

