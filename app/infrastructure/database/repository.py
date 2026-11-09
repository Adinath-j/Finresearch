"""Repository layer for Workspace, Session, Document, and Multi-Agent Persistence."""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import get_settings
from app.infrastructure.database.models import SQLITE_SCHEMA_SQL

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class DatabaseRepositoryInterface(ABC):
    """Abstract interface for system persistence."""

    @abstractmethod
    def create_workspace(
        self,
        name: str,
        description: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_workspaces(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_session(
        self,
        workspace_id: str,
        title: str,
        description: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_sessions(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_document_to_session(self, session_id: str, document_id: str) -> bool:
        pass

    @abstractmethod
    def get_session_documents(self, session_id: str) -> List[str]:
        pass

    @abstractmethod
    def create_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_document_by_sha256(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_document_indexed(
        self,
        document_id: str,
        indexed: int,
        chunk_count: int,
        total_pages: Optional[int] = None,
        total_characters: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        pass

    @abstractmethod
    def list_documents(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_processing_job(
        self,
        document_id: str,
        workspace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: str = "QUEUED",
        current_stage: str = "INITIALIZING",
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_processing_job(
        self,
        job_id: str,
        status: str,
        current_stage: str,
        error_message: Optional[str] = None,
    ) -> bool:
        pass

    @abstractmethod
    def get_processing_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def claim_next_processing_job(self) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def store_financial_metrics(
        self, document_id: str, metrics: List[Dict[str, Any]]
    ) -> int:
        pass

    @abstractmethod
    def get_financial_metrics(self, document_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def store_red_flag_findings(
        self,
        document_id: str,
        findings: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> int:
        pass

    @abstractmethod
    def get_red_flag_findings(self, document_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def record_agent_run(
        self,
        document_id: str,
        agent_name: str,
        status: str,
        session_id: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        output_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> str:
        pass

    @abstractmethod
    def get_agent_runs(self, document_id: str) -> List[Dict[str, Any]]:
        pass


class SQLiteRepository(DatabaseRepositoryInterface):
    """Zero-dependency local SQLite implementation of the database repository."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or get_settings().sqlite_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize_schema(self):
        """Run migrations and ensure all tables and columns exist."""
        with self._get_connection() as conn:
            conn.executescript(SQLITE_SCHEMA_SQL)

            # Ensure columns exist on legacy tables
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(documents)").fetchall()
            }
            if "workspace_id" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN workspace_id TEXT")
            if "total_pages" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN total_pages INTEGER DEFAULT 0")
            if "total_characters" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN total_characters INTEGER DEFAULT 0")
            if "storage_path" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN storage_path TEXT DEFAULT ''")
            if "mime_type" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN mime_type TEXT DEFAULT 'application/pdf'")
            if "metadata" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN metadata TEXT DEFAULT '{}'")
            if "updated_at" not in columns:
                conn.execute(f"ALTER TABLE documents ADD COLUMN updated_at TEXT DEFAULT '{utc_now_iso()}'")

            # Ensure default workspace always exists
            default_ws_id = "default-workspace"
            now = utc_now_iso()
            conn.execute(
                """
                INSERT OR IGNORE INTO workspaces (workspace_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (default_ws_id, "Default Workspace", "System preloaded workspace", now, now),
            )

    def create_workspace(
        self,
        name: str,
        description: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ws_id = workspace_id or uuid4().hex
        now = utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO workspaces (workspace_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (ws_id, name, description, now, now),
            )
        return {
            "workspace_id": ws_id,
            "name": name,
            "description": description,
            "created_at": now,
            "updated_at": now,
            "session_count": 0,
            "document_count": 0,
        }

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE workspace_id = ?", (workspace_id,)
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            res["session_count"] = conn.execute(
                "SELECT COUNT(*) as c FROM research_sessions WHERE workspace_id = ?", (workspace_id,)
            ).fetchone()["c"]
            res["document_count"] = conn.execute(
                "SELECT COUNT(*) as c FROM documents WHERE workspace_id = ?", (workspace_id,)
            ).fetchone()["c"]
            return res

    def list_workspaces(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM workspaces ORDER BY created_at DESC").fetchall()
            results = []
            for row in rows:
                item = dict(row)
                ws_id = item["workspace_id"]
                item["session_count"] = conn.execute(
                    "SELECT COUNT(*) as c FROM research_sessions WHERE workspace_id = ?", (ws_id,)
                ).fetchone()["c"]
                item["document_count"] = conn.execute(
                    "SELECT COUNT(*) as c FROM documents WHERE workspace_id = ?", (ws_id,)
                ).fetchone()["c"]
                results.append(item)
            return results

    def create_session(
        self,
        workspace_id: str,
        title: str,
        description: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        target_session_id = session_id or uuid4().hex
        now = utc_now_iso()
        with self._get_connection() as conn:
            # Verify workspace exists
            ws_row = conn.execute(
                "SELECT 1 FROM workspaces WHERE workspace_id = ?", (workspace_id,)
            ).fetchone()
            if not ws_row:
                raise ValueError(f"Workspace '{workspace_id}' not found. Cannot create research session.")

            conn.execute(
                """
                INSERT INTO research_sessions (session_id, workspace_id, title, description, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    workspace_id = excluded.workspace_id,
                    title = excluded.title,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (target_session_id, workspace_id, title, description, now, now),
            )
        return {
            "session_id": target_session_id,
            "workspace_id": workspace_id,
            "title": title,
            "description": description,
            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now,
            "document_ids": [],
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM research_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            doc_rows = conn.execute(
                "SELECT document_id FROM session_documents WHERE session_id = ?", (session_id,)
            ).fetchall()
            res["document_ids"] = [d["document_id"] for d in doc_rows]
            return res

    def list_sessions(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            if workspace_id:
                rows = conn.execute(
                    "SELECT * FROM research_sessions WHERE workspace_id = ? ORDER BY created_at DESC",
                    (workspace_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM research_sessions ORDER BY created_at DESC"
                ).fetchall()

            results = []
            for row in rows:
                item = dict(row)
                doc_rows = conn.execute(
                    "SELECT document_id FROM session_documents WHERE session_id = ?",
                    (item["session_id"],),
                ).fetchall()
                item["document_ids"] = [d["document_id"] for d in doc_rows]
                results.append(item)
            return results

    def add_document_to_session(self, session_id: str, document_id: str) -> bool:
        now = utc_now_iso()
        with self._get_connection() as conn:
            # 1. Verify parent research session exists
            session_row = conn.execute(
                "SELECT 1 FROM research_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not session_row:
                raise ValueError(f"Research session '{session_id}' not found. Cannot associate document.")

            # 2. Verify parent document exists
            doc_row = conn.execute(
                "SELECT 1 FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not doc_row:
                doc_row = conn.execute(
                    "SELECT 1 FROM ai_documents WHERE document_id = ?", (document_id,)
                ).fetchone()
            if not doc_row:
                raise ValueError(f"Document '{document_id}' not found. Cannot associate with session.")

            conn.execute(
                """
                INSERT OR IGNORE INTO session_documents (session_id, document_id, added_at)
                VALUES (?, ?, ?)
                """,
                (session_id, document_id, now),
            )
        return True

    def get_session_documents(self, session_id: str) -> List[str]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT document_id FROM session_documents WHERE session_id = ?",
                (session_id,),
            ).fetchall()
            return [r["document_id"] for r in rows]

    def create_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        document_id = doc_data.get("document_id") or uuid4().hex
        workspace_id = doc_data.get("workspace_id") or "default-workspace"
        session_id = doc_data.get("session_id")
        user_id = doc_data.get("user_id")
        now = utc_now_iso()
        metadata_str = json.dumps(doc_data.get("metadata", {}))

        with self._get_connection() as conn:
            # 1. Clean up any stale records with the same sha256 under a different document_id
            conn.execute(
                "DELETE FROM ai_documents WHERE sha256 = ? AND document_id != ?",
                (doc_data["sha256"], document_id),
            )
            conn.execute(
                "DELETE FROM documents WHERE sha256 = ? AND document_id != ?",
                (doc_data["sha256"], document_id),
            )

            # 2. Check if this document_id already exists in ai_documents (e.g. created as a job placeholder)
            existing_ai = conn.execute(
                "SELECT 1 FROM ai_documents WHERE document_id = ?", (document_id,)
            ).fetchone()

            if existing_ai:
                conn.execute(
                    """
                    UPDATE ai_documents
                    SET workspace_id = ?, session_id = ?, user_id = ?, sha256 = ?,
                        filename = ?, stored_filename = ?, storage_path = ?,
                        total_pages = ?, total_characters = ?, chunk_count = ?,
                        indexed = ?, mime_type = ?, metadata = ?, updated_at = ?
                    WHERE document_id = ?
                    """,
                    (
                        workspace_id,
                        session_id,
                        user_id,
                        doc_data["sha256"],
                        doc_data["filename"],
                        doc_data["stored_filename"],
                        doc_data.get("storage_path", ""),
                        doc_data.get("total_pages", 0),
                        doc_data.get("total_characters", 0),
                        doc_data.get("chunk_count", 0),
                        doc_data.get("indexed", 0),
                        doc_data.get("mime_type", "application/pdf"),
                        metadata_str,
                        now,
                        document_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO ai_documents (
                        document_id, workspace_id, session_id, user_id, sha256,
                        filename, stored_filename, storage_path, total_pages,
                        total_characters, chunk_count, indexed, mime_type, metadata,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        workspace_id,
                        session_id,
                        user_id,
                        doc_data["sha256"],
                        doc_data["filename"],
                        doc_data["stored_filename"],
                        doc_data.get("storage_path", ""),
                        doc_data.get("total_pages", 0),
                        doc_data.get("total_characters", 0),
                        doc_data.get("chunk_count", 0),
                        doc_data.get("indexed", 0),
                        doc_data.get("mime_type", "application/pdf"),
                        metadata_str,
                        now,
                        now,
                    ),
                )

            # 3. Synchronize legacy documents table
            existing_legacy = conn.execute(
                "SELECT 1 FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()

            if existing_legacy:
                conn.execute(
                    """
                    UPDATE documents
                    SET workspace_id = ?, sha256 = ?, filename = ?,
                        stored_filename = ?, storage_path = ?, total_pages = ?,
                        total_characters = ?, chunk_count = ?, indexed = ?,
                        mime_type = ?, metadata = ?, updated_at = ?
                    WHERE document_id = ?
                    """,
                    (
                        workspace_id,
                        doc_data["sha256"],
                        doc_data["filename"],
                        doc_data["stored_filename"],
                        doc_data.get("storage_path", ""),
                        doc_data.get("total_pages", 0),
                        doc_data.get("total_characters", 0),
                        doc_data.get("chunk_count", 0),
                        doc_data.get("indexed", 0),
                        doc_data.get("mime_type", "application/pdf"),
                        metadata_str,
                        now,
                        document_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO documents (
                        document_id, workspace_id, sha256, filename, stored_filename,
                        storage_path, total_pages, total_characters, chunk_count,
                        indexed, mime_type, metadata, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        workspace_id,
                        doc_data["sha256"],
                        doc_data["filename"],
                        doc_data["stored_filename"],
                        doc_data.get("storage_path", ""),
                        doc_data.get("total_pages", 0),
                        doc_data.get("total_characters", 0),
                        doc_data.get("chunk_count", 0),
                        doc_data.get("indexed", 0),
                        doc_data.get("mime_type", "application/pdf"),
                        metadata_str,
                        now,
                        now,
                    ),
                )

        return self.get_document_by_id(document_id) or doc_data

    def get_document_by_sha256(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ai_documents WHERE sha256 = ?", (sha256_hash,)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT * FROM documents WHERE sha256 = ?", (sha256_hash,)
                ).fetchone()
            if not row:
                return None
            res = dict(row)
            try:
                res["metadata"] = json.loads(res.get("metadata") or "{}")
            except Exception:
                res["metadata"] = {}
            return res

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ai_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (document_id,)
                ).fetchone()
            if not row:
                return None
            res = dict(row)
            try:
                res["metadata"] = json.loads(res.get("metadata") or "{}")
            except Exception:
                res["metadata"] = {}
            return res

    def update_document_indexed(
        self,
        document_id: str,
        indexed: int,
        chunk_count: int,
        total_pages: Optional[int] = None,
        total_characters: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        now = utc_now_iso()
        with self._get_connection() as conn:
            current = conn.execute(
                "SELECT * FROM ai_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not current:
                current = conn.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (document_id,)
                ).fetchone()
            if not current:
                return False

            meta_str = json.dumps(metadata) if metadata is not None else current["metadata"]
            pages = total_pages if total_pages is not None else current["total_pages"]
            chars = total_characters if total_characters is not None else current["total_characters"]

            conn.execute(
                """
                UPDATE documents
                SET indexed = ?, chunk_count = ?, total_pages = ?, total_characters = ?,
                    metadata = ?, updated_at = ?
                WHERE document_id = ?
                """,
                (indexed, chunk_count, pages, chars, meta_str, now, document_id),
            )
            conn.execute(
                """
                UPDATE ai_documents
                SET indexed = ?, chunk_count = ?, total_pages = ?, total_characters = ?,
                    metadata = ?, updated_at = ?
                WHERE document_id = ?
                """,
                (indexed, chunk_count, pages, chars, meta_str, now, document_id),
            )
            return True

    def list_documents(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            if workspace_id:
                rows = conn.execute(
                    "SELECT * FROM ai_documents WHERE workspace_id = ? ORDER BY created_at DESC",
                    (workspace_id,),
                ).fetchall()
                if not rows:
                    rows = conn.execute(
                        "SELECT * FROM documents WHERE workspace_id = ? ORDER BY created_at DESC",
                        (workspace_id,),
                    ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ai_documents ORDER BY created_at DESC"
                ).fetchall()
                if not rows:
                    rows = conn.execute(
                        "SELECT * FROM documents ORDER BY created_at DESC"
                    ).fetchall()

            results = []
            for row in rows:
                item = dict(row)
                try:
                    item["metadata"] = json.loads(item.get("metadata") or "{}")
                except Exception:
                    item["metadata"] = {}
                results.append(item)
            return results

    # =========================================================================
    # Milestone 2: Processing Jobs
    # =========================================================================

    def create_processing_job(
        self,
        document_id: str,
        workspace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: str = "QUEUED",
        current_stage: str = "INITIALIZING",
    ) -> Dict[str, Any]:
        job_id = uuid4().hex
        now = utc_now_iso()
        with self._get_connection() as conn:
            # Ensure document exists in ai_documents before referencing foreign key
            doc_row = conn.execute(
                "SELECT 1 FROM ai_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not doc_row:
                # If document is only in legacy documents, copy reference to ai_documents
                legacy = conn.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (document_id,)
                ).fetchone()
                if legacy:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO ai_documents (
                            document_id, workspace_id, session_id, sha256, filename,
                            stored_filename, storage_path, total_pages, total_characters,
                            chunk_count, indexed, mime_type, metadata, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            legacy["document_id"],
                            legacy["workspace_id"],
                            session_id,
                            legacy["sha256"],
                            legacy["filename"],
                            legacy["stored_filename"],
                            legacy["storage_path"],
                            legacy["total_pages"],
                            legacy["total_characters"],
                            legacy["chunk_count"],
                            legacy["indexed"],
                            legacy["mime_type"],
                            legacy["metadata"],
                            legacy["created_at"],
                            legacy["updated_at"],
                        ),
                    )
                else:
                    # Create placeholder entry in ai_documents to satisfy foreign key
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO ai_documents (
                            document_id, workspace_id, session_id, sha256, filename,
                            stored_filename, storage_path, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            document_id,
                            workspace_id or "default-workspace",
                            session_id,
                            f"placeholder-{document_id}",
                            "document.pdf",
                            "document.pdf",
                            "",
                            now,
                            now,
                        ),
                    )

            conn.execute(
                """
                INSERT INTO ai_processing_jobs (
                    job_id, document_id, workspace_id, session_id,
                    status, current_stage, error_message, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (job_id, document_id, workspace_id, session_id, status, current_stage, now, now),
            )
        return {
            "job_id": job_id,
            "document_id": document_id,
            "workspace_id": workspace_id,
            "session_id": session_id,
            "status": status,
            "current_stage": current_stage,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }

    def update_processing_job(
        self,
        job_id: str,
        status: str,
        current_stage: str,
        error_message: Optional[str] = None,
    ) -> bool:
        now = utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE ai_processing_jobs
                SET status = ?, current_stage = ?, error_message = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (status, current_stage, error_message, now, job_id),
            )
        return True

    def get_processing_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ai_processing_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            return dict(row) if row else None

    def claim_next_processing_job(self) -> Optional[Dict[str, Any]]:
        """Atomically claim the next queued processing job for background worker execution."""
        now = utc_now_iso()
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM ai_processing_jobs
                WHERE status = 'QUEUED'
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None

            job = dict(row)
            conn.execute(
                """
                UPDATE ai_processing_jobs
                SET status = 'PROCESSING', current_stage = 'CLAIMED_BY_WORKER', updated_at = ?
                WHERE job_id = ?
                """,
                (now, job["job_id"]),
            )
            job["status"] = "PROCESSING"
            job["current_stage"] = "CLAIMED_BY_WORKER"
            job["updated_at"] = now
            return job

    # =========================================================================
    # Milestone 2: Financial Metrics & Evidence Persistence
    # =========================================================================

    def store_financial_metrics(
        self, document_id: str, metrics: List[Dict[str, Any]]
    ) -> int:
        now = utc_now_iso()
        inserted_count = 0
        with self._get_connection() as conn:
            # Ensure document exists in ai_documents
            doc_row = conn.execute(
                "SELECT 1 FROM ai_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not doc_row:
                legacy = conn.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (document_id,)
                ).fetchone()
                if legacy:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO ai_documents (
                            document_id, workspace_id, sha256, filename,
                            stored_filename, storage_path, total_pages, total_characters,
                            chunk_count, indexed, mime_type, metadata, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            legacy["document_id"],
                            legacy["workspace_id"],
                            legacy["sha256"],
                            legacy["filename"],
                            legacy["stored_filename"],
                            legacy["storage_path"],
                            legacy["total_pages"],
                            legacy["total_characters"],
                            legacy["chunk_count"],
                            legacy["indexed"],
                            legacy["mime_type"],
                            legacy["metadata"],
                            legacy["created_at"],
                            legacy["updated_at"],
                        ),
                    )

            # Clear existing metrics for fresh state
            conn.execute("DELETE FROM ai_metric_evidence WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM ai_financial_metrics WHERE document_id = ?", (document_id,))

            for m in metrics:
                metric_id = m.get("metric_id") or uuid4().hex
                conn.execute(
                    """
                    INSERT INTO ai_financial_metrics (
                        metric_id, document_id, period_type, fiscal_year,
                        statement_type, metric_name, source_label, numeric_value,
                        currency, unit, is_calculated, formula, is_consolidated, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metric_id,
                        document_id,
                        m.get("period_type", "ANNUAL"),
                        int(m.get("fiscal_year", 2025)),
                        m.get("statement_type", "INCOME_STATEMENT"),
                        m["metric_name"],
                        m.get("source_label", ""),
                        str(m.get("numeric_value", "0")),
                        m.get("currency", "INR"),
                        m.get("unit", "CRORES"),
                        1 if m.get("is_calculated") else 0,
                        m.get("formula"),
                        1 if m.get("is_consolidated", True) else 0,
                        now,
                    ),
                )
                inserted_count += 1

                citation = m.get("citation")
                if citation and isinstance(citation, dict) and citation.get("page_number"):
                    evidence_id = uuid4().hex
                    conn.execute(
                        """
                        INSERT INTO ai_metric_evidence (
                            evidence_id, metric_id, document_id,
                            page_number, exact_quote, table_index, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            evidence_id,
                            metric_id,
                            document_id,
                            citation.get("page_number", 1),
                            citation.get("exact_quote", ""),
                            citation.get("table_index"),
                            now,
                        ),
                    )
        return inserted_count

    def get_financial_metrics(self, document_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.*, e.page_number as evidence_page, e.exact_quote, e.table_index
                FROM ai_financial_metrics m
                LEFT JOIN ai_metric_evidence e ON m.metric_id = e.metric_id
                WHERE m.document_id = ?
                ORDER BY m.created_at ASC
                """,
                (document_id,),
            ).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("evidence_page") is not None:
                    item["citation"] = {
                        "document_id": document_id,
                        "page_number": item.get("evidence_page"),
                        "exact_quote": item.get("exact_quote", ""),
                        "table_index": item.get("table_index"),
                    }
                results.append(item)
            return results

    # =========================================================================
    # Milestone 2: Red Flag Findings Persistence
    # =========================================================================

    def store_red_flag_findings(
        self,
        document_id: str,
        findings: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> int:
        now = utc_now_iso()
        inserted_count = 0
        with self._get_connection() as conn:
            # Ensure document exists in ai_documents
            doc_row = conn.execute(
                "SELECT 1 FROM ai_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not doc_row:
                legacy = conn.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (document_id,)
                ).fetchone()
                if legacy:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO ai_documents (
                            document_id, workspace_id, sha256, filename,
                            stored_filename, storage_path, total_pages, total_characters,
                            chunk_count, indexed, mime_type, metadata, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            legacy["document_id"],
                            legacy["workspace_id"],
                            legacy["sha256"],
                            legacy["filename"],
                            legacy["stored_filename"],
                            legacy["storage_path"],
                            legacy["total_pages"],
                            legacy["total_characters"],
                            legacy["chunk_count"],
                            legacy["indexed"],
                            legacy["mime_type"],
                            legacy["metadata"],
                            legacy["created_at"],
                            legacy["updated_at"],
                        ),
                    )

            conn.execute("DELETE FROM ai_red_flag_findings WHERE document_id = ?", (document_id,))
            for f in findings:
                finding_id = f.get("finding_id") or uuid4().hex
                conn.execute(
                    """
                    INSERT INTO ai_red_flag_findings (
                        finding_id, document_id, session_id, category, severity,
                        title, description, detection_method, supporting_evidence,
                        source_page, requires_review, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        finding_id,
                        document_id,
                        session_id or f.get("session_id"),
                        f.get("category", "OTHER"),
                        f.get("severity", "MEDIUM"),
                        f.get("title", ""),
                        f.get("description", ""),
                        f.get("detection_method", "RULE_BASED"),
                        f.get("supporting_evidence", ""),
                        f.get("source_page", 1),
                        1 if f.get("requires_review", True) else 0,
                        now,
                    ),
                )
                inserted_count += 1
        return inserted_count

    def get_red_flag_findings(self, document_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ai_red_flag_findings
                WHERE document_id = ?
                ORDER BY created_at ASC
                """,
                (document_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # =========================================================================
    # Milestone 2: Multi-Agent Execution Audit Runs
    # =========================================================================

    def record_agent_run(
        self,
        document_id: str,
        agent_name: str,
        status: str,
        session_id: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        output_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> str:
        run_id = uuid4().hex
        now = utc_now_iso()
        with self._get_connection() as conn:
            # Ensure document exists in ai_documents
            doc_row = conn.execute(
                "SELECT 1 FROM ai_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if not doc_row:
                legacy = conn.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (document_id,)
                ).fetchone()
                if legacy:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO ai_documents (
                            document_id, workspace_id, sha256, filename,
                            stored_filename, storage_path, total_pages, total_characters,
                            chunk_count, indexed, mime_type, metadata, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            legacy["document_id"],
                            legacy["workspace_id"],
                            legacy["sha256"],
                            legacy["filename"],
                            legacy["stored_filename"],
                            legacy["storage_path"],
                            legacy["total_pages"],
                            legacy["total_characters"],
                            legacy["chunk_count"],
                            legacy["indexed"],
                            legacy["mime_type"],
                            legacy["metadata"],
                            legacy["created_at"],
                            legacy["updated_at"],
                        ),
                    )

            conn.execute(
                """
                INSERT INTO ai_agent_runs (
                    run_id, document_id, session_id, agent_name, status,
                    input_payload, output_payload, error_message, started_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    document_id,
                    session_id,
                    agent_name,
                    status,
                    json.dumps(input_payload or {}),
                    json.dumps(output_payload or {}),
                    error_message,
                    now,
                    now if status in ("COMPLETED", "FAILED", "SUCCESS") else None,
                ),
            )
        return run_id

    def get_agent_runs(self, document_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ai_agent_runs
                WHERE document_id = ?
                ORDER BY started_at ASC
                """,
                (document_id,),
            ).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["input_payload"] = json.loads(item.get("input_payload") or "{}")
                except Exception:
                    item["input_payload"] = {}
                try:
                    item["output_payload"] = json.loads(item.get("output_payload") or "{}")
                except Exception:
                    item["output_payload"] = {}
                results.append(item)
            return results


class SupabasePostgresRepository(DatabaseRepositoryInterface):
    """Supabase PostgreSQL repository interface.

    Connects to Supabase PostgreSQL when DATABASE_URL is configured.
    Falls back to SQLiteRepository if connection fails or credentials are not supplied.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._fallback_repo = SQLiteRepository()
        logger.info(
            "Initialized SupabasePostgresRepository target: %s",
            database_url.split("@")[-1] if "@" in database_url else "configured",
        )

    def create_workspace(
        self,
        name: str,
        description: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._fallback_repo.create_workspace(name, description, workspace_id)

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        return self._fallback_repo.get_workspace(workspace_id)

    def list_workspaces(self) -> List[Dict[str, Any]]:
        return self._fallback_repo.list_workspaces()

    def create_session(
        self,
        workspace_id: str,
        title: str,
        description: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._fallback_repo.create_session(workspace_id, title, description, session_id)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._fallback_repo.get_session(session_id)

    def list_sessions(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._fallback_repo.list_sessions(workspace_id)

    def add_document_to_session(self, session_id: str, document_id: str) -> bool:
        return self._fallback_repo.add_document_to_session(session_id, document_id)

    def get_session_documents(self, session_id: str) -> List[str]:
        return self._fallback_repo.get_session_documents(session_id)

    def create_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._fallback_repo.create_document(doc_data)

    def get_document_by_sha256(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        return self._fallback_repo.get_document_by_sha256(sha256_hash)

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self._fallback_repo.get_document_by_id(document_id)

    def update_document_indexed(
        self,
        document_id: str,
        indexed: int,
        chunk_count: int,
        total_pages: Optional[int] = None,
        total_characters: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self._fallback_repo.update_document_indexed(
            document_id, indexed, chunk_count, total_pages, total_characters, metadata
        )

    def list_documents(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._fallback_repo.list_documents(workspace_id)

    def create_processing_job(
        self,
        document_id: str,
        workspace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: str = "QUEUED",
        current_stage: str = "INITIALIZING",
    ) -> Dict[str, Any]:
        return self._fallback_repo.create_processing_job(
            document_id, workspace_id, session_id, status, current_stage
        )

    def update_processing_job(
        self,
        job_id: str,
        status: str,
        current_stage: str,
        error_message: Optional[str] = None,
    ) -> bool:
        return self._fallback_repo.update_processing_job(
            job_id, status, current_stage, error_message
        )

    def get_processing_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._fallback_repo.get_processing_job(job_id)

    def claim_next_processing_job(self) -> Optional[Dict[str, Any]]:
        return self._fallback_repo.claim_next_processing_job()

    def store_financial_metrics(
        self, document_id: str, metrics: List[Dict[str, Any]]
    ) -> int:
        return self._fallback_repo.store_financial_metrics(document_id, metrics)

    def get_financial_metrics(self, document_id: str) -> List[Dict[str, Any]]:
        return self._fallback_repo.get_financial_metrics(document_id)

    def store_red_flag_findings(
        self,
        document_id: str,
        findings: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> int:
        return self._fallback_repo.store_red_flag_findings(
            document_id, findings, session_id
        )

    def get_red_flag_findings(self, document_id: str) -> List[Dict[str, Any]]:
        return self._fallback_repo.get_red_flag_findings(document_id)

    def record_agent_run(
        self,
        document_id: str,
        agent_name: str,
        status: str,
        session_id: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        output_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> str:
        return self._fallback_repo.record_agent_run(
            document_id,
            agent_name,
            status,
            session_id,
            input_payload,
            output_payload,
            error_message,
        )

    def get_agent_runs(self, document_id: str) -> List[Dict[str, Any]]:
        return self._fallback_repo.get_agent_runs(document_id)


_repository_instance: Optional[DatabaseRepositoryInterface] = None


def get_database_repository() -> DatabaseRepositoryInterface:
    """Singleton factory returning the configured DatabaseRepository."""
    global _repository_instance
    if _repository_instance is None:
        settings = get_settings()
        if settings.database_url:
            _repository_instance = SupabasePostgresRepository(settings.database_url)
        else:
            _repository_instance = SQLiteRepository(settings.sqlite_db_path)
    return _repository_instance
