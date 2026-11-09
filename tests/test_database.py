"""Test suite for Database Repositories (Workspaces, Sessions, Documents)."""

import tempfile
import unittest
from pathlib import Path
from app.infrastructure.database import SQLiteRepository


class TestDatabaseRepository(unittest.TestCase):
    """Unit tests for SQLite repository supporting workspaces and sessions."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_documents.db"
        self.repo = SQLiteRepository(db_path=str(self.db_path))

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_workspace_lifecycle(self):
        ws = self.repo.create_workspace(
            name="Vidzai Financial Lab",
            description="Infosys Springboard Workspace",
        )
        self.assertIsNotNone(ws["workspace_id"])
        self.assertEqual(ws["name"], "Vidzai Financial Lab")

        fetched = self.repo.get_workspace(ws["workspace_id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Vidzai Financial Lab")

        all_ws = self.repo.list_workspaces()
        # Default workspace + new workspace
        self.assertGreaterEqual(len(all_ws), 2)

    def test_research_session_lifecycle(self):
        ws = self.repo.create_workspace(name="Equity Research")
        session = self.repo.create_session(
            workspace_id=ws["workspace_id"],
            title="Q4 IT Sector Benchmarking",
            description="Comparing Indian IT majors",
        )
        self.assertIsNotNone(session["session_id"])
        self.assertEqual(session["title"], "Q4 IT Sector Benchmarking")
        self.assertEqual(session["status"], "ACTIVE")

        # Document association
        doc_data = {
            "document_id": "test-doc-abc",
            "workspace_id": ws["workspace_id"],
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "filename": "q4_report.pdf",
            "stored_filename": "test-doc-abc.pdf",
            "total_pages": 45,
            "total_characters": 89000,
            "chunk_count": 50,
            "indexed": 1,
        }
        self.repo.create_document(doc_data)
        self.repo.add_document_to_session(session["session_id"], "test-doc-abc")

        session_docs = self.repo.get_session_documents(session["session_id"])
        self.assertIn("test-doc-abc", session_docs)

    def test_duplicate_document_lookup_by_sha256(self):
        file_hash = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"
        doc_data = {
            "document_id": "doc-unique-1",
            "sha256": file_hash,
            "filename": "filing.pdf",
            "stored_filename": "doc-unique-1.pdf",
            "indexed": 1,
            "chunk_count": 10,
        }
        self.repo.create_document(doc_data)

        duplicate = self.repo.get_document_by_sha256(file_hash)
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate["document_id"], "doc-unique-1")

    def test_milestone2_repository_methods(self):
        doc_data = {
            "document_id": "doc-m2-repo-test",
            "sha256": "abcdef998877665544332211aabbccddeeff00112233445566778899aabbccdd",
            "filename": "m2_report.pdf",
            "stored_filename": "doc-m2-repo-test.pdf",
            "indexed": 1,
            "chunk_count": 5,
        }
        self.repo.create_document(doc_data)

        # Processing Job
        job = self.repo.create_processing_job("doc-m2-repo-test")
        self.assertIsNotNone(job["job_id"])
        self.assertEqual(job["status"], "QUEUED")

        self.repo.update_processing_job(job["job_id"], status="COMPLETED", current_stage="DONE")
        updated_job = self.repo.get_processing_job(job["job_id"])
        self.assertEqual(updated_job["status"], "COMPLETED")

        # Financial Metrics
        metrics = [
            {
                "metric_name": "REVENUE",
                "source_label": "Revenue from operations",
                "numeric_value": "125000",
                "fiscal_year": 2025,
                "citation": {"page_number": 1, "exact_quote": "Revenue: 125,000"},
            }
        ]
        stored_count = self.repo.store_financial_metrics("doc-m2-repo-test", metrics)
        self.assertEqual(stored_count, 1)

        db_metrics = self.repo.get_financial_metrics("doc-m2-repo-test")
        self.assertEqual(len(db_metrics), 1)
        self.assertEqual(db_metrics[0]["metric_name"], "REVENUE")
        self.assertEqual(db_metrics[0]["numeric_value"], "125000")

        # Red Flag Findings
        findings = [
            {
                "category": "LIQUIDITY",
                "severity": "HIGH",
                "title": "Low Working Capital",
                "description": "Current ratio below safe margin",
                "supporting_evidence": "Current ratio is 0.85",
                "source_page": 2,
            }
        ]
        rf_count = self.repo.store_red_flag_findings("doc-m2-repo-test", findings)
        self.assertEqual(rf_count, 1)

        db_findings = self.repo.get_red_flag_findings("doc-m2-repo-test")
        self.assertEqual(len(db_findings), 1)
        self.assertEqual(db_findings[0]["title"], "Low Working Capital")

        # Agent Runs
        run_id = self.repo.record_agent_run(
            document_id="doc-m2-repo-test",
            agent_name="TEST_AGENT",
            status="COMPLETED",
        )
        self.assertIsNotNone(run_id)

        runs = self.repo.get_agent_runs("doc-m2-repo-test")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["agent_name"], "TEST_AGENT")

    def test_add_document_to_session_missing_session_raises(self):
        """Task 7 Requirement: Verify adding document to a missing research session raises ValueError."""
        doc_data = {
            "document_id": "doc-fk-test-1",
            "sha256": "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
            "filename": "fk_test.pdf",
            "stored_filename": "doc-fk-test-1.pdf",
            "indexed": 1,
            "chunk_count": 2,
        }
        self.repo.create_document(doc_data)

        with self.assertRaises(ValueError) as ctx:
            self.repo.add_document_to_session(
                session_id="non-existent-session-id",
                document_id="doc-fk-test-1",
            )
        self.assertIn("not found", str(ctx.exception).lower())

    def test_add_document_to_session_missing_document_raises(self):
        """Task 7 Requirement: Verify adding a missing document to a session raises ValueError."""
        ws = self.repo.create_workspace("FK Test Workspace")
        session = self.repo.create_session(ws["workspace_id"], "FK Test Session")

        with self.assertRaises(ValueError) as ctx:
            self.repo.add_document_to_session(
                session_id=session["session_id"],
                document_id="non-existent-document-id",
            )
        self.assertIn("not found", str(ctx.exception).lower())

    def test_add_document_to_session_success(self):
        """Task 7 Requirement: Verify associating an existing document with a valid session succeeds."""
        ws = self.repo.create_workspace("Association Test Workspace")
        session = self.repo.create_session(ws["workspace_id"], "Association Session")

        doc_data = {
            "document_id": "doc-assoc-success",
            "sha256": "112233aabbcc445566ddeeff77889900112233aabbcc445566ddeeff77889900",
            "filename": "assoc_test.pdf",
            "stored_filename": "doc-assoc-success.pdf",
            "indexed": 1,
            "chunk_count": 3,
        }
        self.repo.create_document(doc_data)

        result = self.repo.add_document_to_session(session["session_id"], "doc-assoc-success")
        self.assertTrue(result)

        docs = self.repo.get_session_documents(session["session_id"])
        self.assertIn("doc-assoc-success", docs)

    def test_claim_next_processing_job_atomic(self):
        doc_data = {
            "document_id": "doc-job-claim-test",
            "sha256": "99887766554433221100aabbccddeeff99887766554433221100aabbccddeeff",
            "filename": "claim_test.pdf",
            "stored_filename": "doc-job-claim-test.pdf",
            "indexed": 1,
            "chunk_count": 2,
        }
        self.repo.create_document(doc_data)

        # Initially no queued jobs
        self.assertIsNone(self.repo.claim_next_processing_job())

        # Create a queued job
        job = self.repo.create_processing_job("doc-job-claim-test", status="QUEUED")
        self.assertEqual(job["status"], "QUEUED")

        # Claim job atomically
        claimed = self.repo.claim_next_processing_job()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["job_id"], job["job_id"])
        self.assertEqual(claimed["status"], "PROCESSING")
        self.assertEqual(claimed["current_stage"], "CLAIMED_BY_WORKER")

        # No more queued jobs
        self.assertIsNone(self.repo.claim_next_processing_job())


if __name__ == "__main__":
    unittest.main()
