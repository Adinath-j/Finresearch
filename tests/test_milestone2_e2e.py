"""End-to-End Test for Milestone 2: Multi-Agent Ingestion, Extraction, and Risk Analysis."""

import unittest
from pathlib import Path
from app.infrastructure.database import get_database_repository
from app.orchestration.workflow import MultiAgentWorkflowOrchestrator


class TestMilestone2EndToEnd(unittest.TestCase):
    """End-to-end pipeline test running Document Agent -> Extraction Agent -> Red Flag Agent."""

    def setUp(self):
        self.seed_file = Path("seed_documents/acme_tech_10k_fy25.pdf")
        if not self.seed_file.exists():
            from app.infrastructure.document_processing.seed_generator import generate_seed_pdf_files
            generate_seed_pdf_files(Path("seed_documents"))
        self.repo = get_database_repository()
        self.workspace_id = "default-workspace"
        self.session_id = "test-session-m2"

        # 1. Ensure the required workspace exists
        if not self.repo.get_workspace(self.workspace_id):
            self.repo.create_workspace(
                name="Default Workspace",
                description="Default Workspace for E2E Tests",
                workspace_id=self.workspace_id,
            )

        # 2. Ensure the research session exists and references a valid workspace
        if not self.repo.get_session(self.session_id):
            self.repo.create_session(
                workspace_id=self.workspace_id,
                title="Acme Tech FY25 Analysis Session",
                description="E2E Research Session for Milestone 2",
                session_id=self.session_id,
            )

    def test_milestone2_pipeline_execution(self):
        if not self.seed_file.exists():
            self.skipTest("Seed document acme_tech_10k_fy25.pdf not found.")

        file_bytes = self.seed_file.read_bytes()

        # Run 3-agent pipeline
        final_state = MultiAgentWorkflowOrchestrator.run_pipeline(
            document_id="acme-test-m2-e2e",
            filename=self.seed_file.name,
            file_bytes=file_bytes,
            workspace_id=self.workspace_id,
            session_id=self.session_id,
        )

        self.assertFalse(final_state.is_failed)
        self.assertEqual(final_state.current_phase, "COMPLETED")
        self.assertTrue(final_state.is_indexed)
        self.assertGreater(final_state.total_pages, 0)
        self.assertGreater(final_state.chunk_count, 0)

        # Verify Extraction Agent output
        self.assertIsNotNone(final_state.extracted_financials)
        self.assertGreater(final_state.extracted_metrics_count, 0)
        metrics = final_state.extracted_financials.get("metrics", {})
        self.assertIn("REVENUE", metrics)
        self.assertEqual(metrics["REVENUE"]["value"], "14300.00")

        # Verify Red Flag Agent output
        self.assertIsNotNone(final_state.red_flag_findings)

        # Verify database persistence
        db_metrics = self.repo.get_financial_metrics("acme-test-m2-e2e")
        self.assertGreater(len(db_metrics), 0)

        db_findings = self.repo.get_red_flag_findings("acme-test-m2-e2e")
        self.assertIsInstance(db_findings, list)

        # Verify agent execution runs recorded
        runs = self.repo.get_agent_runs("acme-test-m2-e2e")
        self.assertGreaterEqual(len(runs), 1)

        # Verify document successfully associated with research session
        session_docs = self.repo.get_session_documents(self.session_id)
        self.assertIn("acme-test-m2-e2e", session_docs)


if __name__ == "__main__":
    unittest.main()

