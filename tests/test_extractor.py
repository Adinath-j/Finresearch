"""Unit tests for MetricExtractor and ExtractionAgentService."""

import unittest
from decimal import Decimal
from app.agents.extraction_agent.extractor import MetricExtractor
from app.agents.extraction_agent.service import ExtractionAgentService
from app.infrastructure.database import SQLiteRepository
from app.infrastructure.llm import MockLLMProvider
import tempfile
from pathlib import Path


class TestMetricExtractor(unittest.TestCase):
    """Test suite for extracting financial statements and ratios from table chunks."""

    def setUp(self):
        self.mock_llm = MockLLMProvider()
        self.extractor = MetricExtractor(llm_provider=self.mock_llm)

    def test_extract_from_table_chunk(self):
        table_markdown = (
            "### Financial Table (Page 1)\n"
            "| Particulars | 2025 | 2024 |\n"
            "| --- | --- | --- |\n"
            "| Total Revenue | 14,300 | 11,800 |\n"
            "| Cost of revenue | 4,550 | 3,900 |\n"
            "| Gross profit | 9,750 | 7,900 |\n"
            "| Operating income | 1,600 | 1,150 |\n"
            "| Net income | 1,184 | 832 |\n"
            "| Total current assets | 7,950 | 6,620 |\n"
            "| Total current liabilities | 5,000 | 4,210 |\n"
            "| Long-term debt | 2,500 | 2,500 |\n"
            "| Total stockholders equity | 9,900 | 8,660 |\n"
            "| Operating cash flow | 3,150 | 2,800 |\n"
            "| Capital expenditures | 1,400 | 1,200 |\n"
        )
        sample_chunk = {
            "chunk_id": "doc-test-1",
            "document_id": "doc-test",
            "filename": "annual_report.pdf",
            "page_number": 1,
            "is_table": True,
            "text": table_markdown,
        }

        financials = self.extractor.extract_from_chunks(
            document_id="doc-test",
            filename="annual_report.pdf",
            chunks=[sample_chunk],
            company_name="Acme Corp",
        )

        self.assertEqual(financials.document_id, "doc-test")
        self.assertEqual(financials.company_name, "Acme Corp")

        # Verify core statement metrics
        self.assertIn("REVENUE", financials.income_statement)
        self.assertEqual(financials.income_statement["REVENUE"].value, Decimal("14300"))
        self.assertEqual(financials.income_statement["REVENUE"].citation.page_number, 1)

        self.assertIn("GROSS_PROFIT", financials.income_statement)
        self.assertEqual(financials.income_statement["GROSS_PROFIT"].value, Decimal("9750"))

        self.assertIn("NET_INCOME", financials.income_statement)
        self.assertEqual(financials.income_statement["NET_INCOME"].value, Decimal("1184"))

        self.assertIn("CURRENT_ASSETS", financials.balance_sheet)
        self.assertEqual(financials.balance_sheet["CURRENT_ASSETS"].value, Decimal("7950"))

        self.assertIn("TOTAL_DEBT", financials.balance_sheet)
        self.assertEqual(financials.balance_sheet["TOTAL_DEBT"].value, Decimal("2500"))

        # Verify deterministic calculated ratios
        self.assertIn("GROSS_MARGIN", financials.ratios)
        self.assertEqual(financials.ratios["GROSS_MARGIN"].value, Decimal("68.18"))
        self.assertTrue(financials.ratios["GROSS_MARGIN"].is_calculated)

        self.assertIn("CURRENT_RATIO", financials.ratios)
        self.assertEqual(financials.ratios["CURRENT_RATIO"].value, Decimal("1.59"))

        self.assertIn("FREE_CASH_FLOW", financials.ratios)
        self.assertEqual(financials.ratios["FREE_CASH_FLOW"].value, Decimal("1750.00"))


class TestExtractionAgentService(unittest.TestCase):
    """Integration test suite for ExtractionAgentService with repository persistence."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_extract.db"
        self.repo = SQLiteRepository(db_path=str(self.db_path))
        self.mock_llm = MockLLMProvider()
        self.extractor = MetricExtractor(llm_provider=self.mock_llm)
        self.service = ExtractionAgentService(
            repository=self.repo,
            extractor=self.extractor,
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_service_extraction_and_persistence(self):
        # Create document record first
        doc_data = {
            "document_id": "doc-extract-101",
            "workspace_id": "ws-1",
            "sha256": "aabbcc11223344556677889900aabbcc11223344556677889900aabbcc112233",
            "filename": "tech_10k.pdf",
            "stored_filename": "tech_10k.pdf",
            "total_pages": 5,
            "chunk_count": 10,
            "indexed": 1,
        }
        self.repo.create_document(doc_data)

        table_markdown = (
            "| Particulars | 2025 |\n"
            "| --- | --- |\n"
            "| Revenue from operations | 25,000 |\n"
            "| Profit for the period | 4,500 |\n"
            "| Total current assets | 12,000 |\n"
            "| Total current liabilities | 6,000 |\n"
        )
        sample_chunk = {
            "chunk_id": "c-1",
            "document_id": "doc-extract-101",
            "filename": "tech_10k.pdf",
            "page_number": 2,
            "is_table": True,
            "text": table_markdown,
        }

        financials = self.service.extract_document_financials(
            document_id="doc-extract-101",
            chunks=[sample_chunk],
        )

        self.assertIsNotNone(financials)
        self.assertIn("REVENUE", financials.income_statement)

        # Check repository persistence
        stored = self.service.get_extracted_financials("doc-extract-101")
        self.assertIsNotNone(stored)
        self.assertGreater(stored["total_metrics"], 0)
        self.assertIn("REVENUE", stored["metrics"])
        self.assertEqual(stored["metrics"]["REVENUE"]["numeric_value"], "25000")


if __name__ == "__main__":
    unittest.main()

