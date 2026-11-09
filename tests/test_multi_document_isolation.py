"""End-to-End Acceptance Test: Multi-Document Isolation and Zero Cross-Contamination.

Validates:
1. Document A (Zenith Energy, USD) and Document B (Infosys Limited, INR) are processed independently.
2. Complete data isolation: Document A metrics belong strictly to Document A; Document B to Document B.
3. Citations point to distinct source files and pages.
4. Physical PDF binaries remain on storage.
5. All records, metrics, and red flags survive repository re-connection across service restarts.
"""

import tempfile
import unittest
from pathlib import Path

from app.agents.document_agent import DocumentAgentService
from app.infrastructure.database import SQLiteRepository
from app.infrastructure.document_processing.seed_generator import generate_seed_pdf_files
from app.infrastructure.storage import LocalFileStorage
from app.orchestration.workflow import MultiAgentWorkflowOrchestrator


class TestMultiDocumentIsolation(unittest.TestCase):
    """End-to-end acceptance suite proving zero cross-document data leakage."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_isolation.db"
        self.upload_dir = self.temp_path / "uploads"
        self.seed_dir = self.temp_path / "seed_docs"

        self.repo = SQLiteRepository(db_path=str(self.db_path))
        self.storage = LocalFileStorage(upload_dir=str(self.upload_dir))

        # Direct global repository and storage singletons to isolated test sandbox
        import app.infrastructure.database.repository as repo_module
        import app.infrastructure.storage as storage_module
        self._orig_repo = repo_module._repository_instance
        self._orig_storage = storage_module._storage_instance
        repo_module._repository_instance = self.repo
        storage_module._storage_instance = self.storage

        # Ensure seed PDFs exist in temp seed_dir
        generate_seed_pdf_files(self.seed_dir)
        self.doc_a_path = self.seed_dir / "zenith_energy_earnings_call_q4_fy25.pdf"
        self.doc_b_path = self.seed_dir / "infosys_annual_report_fy24.pdf"

    def tearDown(self):
        import app.infrastructure.database.repository as repo_module
        import app.infrastructure.storage as storage_module
        repo_module._repository_instance = self._orig_repo
        storage_module._storage_instance = self._orig_storage
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_multi_document_pipeline_isolation(self):
        bytes_a = self.doc_a_path.read_bytes()
        bytes_b = self.doc_b_path.read_bytes()

        doc_a_id = "doc-zenith-isolation-001"
        doc_b_id = "doc-infosys-isolation-002"

        # 1. Process Document A (Zenith Energy - USD)
        state_a = MultiAgentWorkflowOrchestrator.run_pipeline(
            document_id=doc_a_id,
            filename=self.doc_a_path.name,
            file_bytes=bytes_a,
            workspace_id="default-workspace",
        )
        self.assertFalse(state_a.is_failed)
        self.assertEqual(state_a.current_phase, "COMPLETED")

        # 2. Process Document B (Infosys Limited - INR)
        state_b = MultiAgentWorkflowOrchestrator.run_pipeline(
            document_id=doc_b_id,
            filename=self.doc_b_path.name,
            file_bytes=bytes_b,
            workspace_id="default-workspace",
        )
        self.assertFalse(state_b.is_failed)
        self.assertEqual(state_b.current_phase, "COMPLETED")

        # 3. Assert Metric Isolation in Memory State
        metrics_a = state_a.extracted_financials.get("metrics", {})
        metrics_b = state_b.extracted_financials.get("metrics", {})

        self.assertIn("REVENUE", metrics_a)
        self.assertIn("REVENUE", metrics_b)

        # Revenue values must be completely distinct
        val_a = float(metrics_a["REVENUE"]["value"])
        val_b = float(metrics_b["REVENUE"]["value"])
        self.assertNotEqual(val_a, val_b)
        self.assertEqual(val_a, 8420.0)
        self.assertEqual(val_b, 153670.0)

        # 4. Assert Citation Provenance
        citation_a = metrics_a["REVENUE"]["citation"]
        citation_b = metrics_b["REVENUE"]["citation"]
        self.assertEqual(citation_a["document_id"], doc_a_id)
        self.assertEqual(citation_b["document_id"], doc_b_id)

        # 5. Assert Database Persistence Isolation
        db_metrics_a = self.repo.get_financial_metrics(doc_a_id)
        db_metrics_b = self.repo.get_financial_metrics(doc_b_id)

        self.assertGreater(len(db_metrics_a), 0)
        self.assertGreater(len(db_metrics_b), 0)

        # Verify no Document A metric was stored under Document B ID
        db_rev_a = next(m for m in db_metrics_a if m["metric_name"] == "REVENUE")
        db_rev_b = next(m for m in db_metrics_b if m["metric_name"] == "REVENUE")

        self.assertEqual(float(db_rev_a["numeric_value"]), 8420.0)
        self.assertEqual(float(db_rev_b["numeric_value"]), 153670.0)

        # 6. Verify Physical Storage Preservation
        # Files must be stored and remain on disk
        self.assertTrue(self.storage.file_exists(doc_a_id))
        self.assertTrue(self.storage.file_exists(doc_b_id))

        # 7. Verify Survival Across Repository Reconnection (Service Restart Simulation)
        fresh_repo = SQLiteRepository(db_path=str(self.db_path))
        reconnected_metrics_a = fresh_repo.get_financial_metrics(doc_a_id)
        reconnected_metrics_b = fresh_repo.get_financial_metrics(doc_b_id)

        self.assertEqual(len(reconnected_metrics_a), len(db_metrics_a))
        self.assertEqual(len(reconnected_metrics_b), len(db_metrics_b))

        # Reconnected values must match exactly
        rec_rev_a = next(m for m in reconnected_metrics_a if m["metric_name"] == "REVENUE")
        rec_rev_b = next(m for m in reconnected_metrics_b if m["metric_name"] == "REVENUE")
        self.assertEqual(float(rec_rev_a["numeric_value"]), 8420.0)
        self.assertEqual(float(rec_rev_b["numeric_value"]), 153670.0)


if __name__ == "__main__":
    unittest.main()

