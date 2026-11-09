"""Test suite for Document Parsing and Table Extraction."""

import unittest
from pathlib import Path
import pymupdf
from app.infrastructure.document_processing.parser import (
    PyMuPDFParser,
    _format_table_markdown,
)


class TestDocumentParser(unittest.TestCase):
    """Unit tests for PDF text and financial table parsing."""

    def setUp(self):
        self.parser = PyMuPDFParser()
        # Create a small in-memory PDF with known text and table
        self.doc = pymupdf.open()
        page = self.doc.new_page(width=612, height=792)
        page.insert_text((50, 50), "FINANCIAL DISCLOSURES", fontsize=14)
        page.insert_text(
            (50, 100),
            "Consolidated revenue for the year reached INR 153,670 Crores with strong growth.",
            fontsize=10,
        )
        self.pdf_bytes = self.doc.tobytes()

    def tearDown(self):
        self.doc.close()

    def test_parse_valid_pdf_extracts_pages(self):
        pages = self.parser.parse_pdf(self.pdf_bytes)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page_number, 1)
        self.assertIn("FINANCIAL DISCLOSURES", pages[0].text)
        self.assertIn("153,670 Crores", pages[0].text)

    def test_format_table_markdown(self):
        raw_table = [
            ["Metric", "FY25", "FY24"],
            ["Revenue", "153670", "146767"],
            ["Net Profit", "26248", "24095"],
        ]
        md = _format_table_markdown(raw_table)
        self.assertIn("| Metric | FY25 | FY24 |", md)
        self.assertIn("| --- | --- | --- |", md)
        self.assertIn("| Revenue | 153670 | 146767 |", md)

    def test_parse_seed_document(self):
        seed_path = Path("seed_documents/zenith_energy_earnings_call_q4_fy25.pdf")
        if seed_path.exists():
            pages = self.parser.parse_pdf(seed_path)
            self.assertGreaterEqual(len(pages), 1)
            self.assertIn("ZENITH ENERGY", pages[0].text)


if __name__ == "__main__":
    unittest.main()

