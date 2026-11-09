"""Durable Database-Backed Multi-Agent Job Worker.

Polls and executes background processing jobs through the LangGraph Multi-Agent Workflow:
Document Agent -> Extraction Agent -> Evidence Validation -> Red Flag Agent -> Persistence.

Usage:
    python worker.py
"""

import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import get_settings
from app.infrastructure.database import get_database_repository
from app.orchestration.workflow import MultiAgentWorkflowOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [worker] %(message)s",
)
logger = logging.getLogger("worker")

_should_exit = False


def _signal_handler(sig, frame):
    global _should_exit
    logger.info("Shutdown signal received (%s). Exiting worker gracefully...", sig)
    _should_exit = True


def recover_stale_jobs(repo):
    """Recover jobs that were left in PROCESSING state from a previous unexpected crash."""
    try:
        if hasattr(repo, "_get_connection"):
            with repo._get_connection() as conn:
                res = conn.execute(
                    """
                    UPDATE ai_processing_jobs
                    SET status = 'QUEUED', current_stage = 'RECOVERED_FROM_CRASH'
                    WHERE status = 'PROCESSING'
                    """
                )
                if res.rowcount > 0:
                    logger.info("Recovered %d orphaned job(s) from previous run back to QUEUED state.", res.rowcount)
    except Exception as e:
        logger.warning("Could not execute stale job recovery on startup: %s", e)


def run_worker():
    """Main worker loop polling ai_processing_jobs."""
    settings = get_settings()
    repo = get_database_repository()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("=" * 65)
    logger.info("Multi-Agent Persistent Job Worker Online")
    logger.info("Polling Database: %s", type(repo).__name__)
    logger.info("Poll Interval: %ds | Max Retries: %d", settings.worker_poll_seconds, settings.worker_max_retries)
    logger.info("Waiting for queued financial document processing jobs...")
    logger.info("=" * 65)

    recover_stale_jobs(repo)

    while not _should_exit:
        try:
            job = repo.claim_next_processing_job()
            if job:
                job_id = job["job_id"]
                doc_id = job["document_id"]
                logger.info(">>> Claimed job %s for document %s", job_id, doc_id)

                doc = repo.get_document_by_id(doc_id)
                filename = doc.get("filename", "document.pdf") if doc else "document.pdf"
                storage_path = doc.get("storage_path") if doc else None

                # Execute sequential multi-agent workflow
                try:
                    final_state = MultiAgentWorkflowOrchestrator.run_pipeline(
                        document_id=doc_id,
                        filename=filename,
                        storage_path=storage_path,
                        workspace_id=job.get("workspace_id") or "default-workspace",
                        session_id=job.get("session_id"),
                        job_id=job_id,
                    )

                    if not final_state.is_failed:
                        repo.update_processing_job(
                            job_id=job_id,
                            status="COMPLETED",
                            current_stage="COMPLETED",
                        )
                        logger.info(
                            "Job %s COMPLETED! Extracted %d metrics, identified %d red flags.",
                            job_id,
                            final_state.extracted_metrics_count,
                            final_state.red_flag_count,
                        )
                    else:
                        err_msg = "; ".join(final_state.errors) if final_state.errors else "Workflow execution failed."
                        repo.update_processing_job(
                            job_id=job_id,
                            status="FAILED",
                            current_stage="FAILED",
                            error_message=err_msg,
                        )
                        logger.error("Job %s FAILED: %s", job_id, err_msg)

                except Exception as exc:
                    logger.exception("Unexpected error executing job %s: %s", job_id, exc)
                    repo.update_processing_job(
                        job_id=job_id,
                        status="FAILED",
                        current_stage="FAILED",
                        error_message=str(exc),
                    )

            else:
                time.sleep(settings.worker_poll_seconds)

        except Exception as e:
            logger.error("Worker polling exception: %s", e)
            time.sleep(settings.worker_poll_seconds)

    logger.info("Worker stopped successfully.")


if __name__ == "__main__":
    run_worker()

