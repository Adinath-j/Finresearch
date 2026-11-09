"""Unit tests for LLM-based Narrative Disclosure Risk Analyzer."""

import unittest
from app.agents.red_flag_agent.analyzer import DisclosureAnalyzer
from app.infrastructure.llm import MockLLMProvider
from app.schemas.agents import RiskCategory, RiskSeverity


class TestDisclosureAnalyzer(unittest.TestCase):
    """Test suite for detecting auditor qualifications and disclosure warnings."""

    def setUp(self):
        self.mock_llm = MockLLMProvider()
        self.analyzer = DisclosureAnalyzer(llm_provider=self.mock_llm)

    def test_auditor_qualification_disclosure_analysis(self):
        chunks = [
            {
                "chunk_id": "c-auditor",
                "page_number": 197,
                "text": (
                    "INDEPENDENT AUDITOR'S REPORT: Key Audit Matter. "
                    "Revenue recognition from fixed price contracts involves management judgement "
                    "and were identified as a key audit matter requiring higher extent of audit effort."
                ),
            }
        ]

        findings = self.analyzer.analyze_disclosures(
            document_id="doc-auditor-101",
            filename="annual_report.pdf",
            chunks=chunks,
            fiscal_year=2026,
        )

        self.assertGreaterEqual(len(findings), 1)
        first = findings[0]
        self.assertEqual(first.category, RiskCategory.AUDITOR_QUALIFICATION)
        self.assertEqual(first.source_citation.page_number, 197)
        self.assertIn("Revenue Recognition", first.title)
        self.assertIsNotNone(first.supporting_evidence)


if __name__ == "__main__":
    unittest.main()

