"""Initial migration creating AI Service namespaced tables for Supabase PostgreSQL.

Revision ID: 001_initial_ai_service_tables
Revises: None
Create Date: 2026-11-04 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_ai_service_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. ai_documents
    op.create_table(
        "ai_documents",
        sa.Column("document_id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("user_id", sa.String(64), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("total_pages", sa.Integer(), server_default="0"),
        sa.Column("total_characters", sa.Integer(), server_default="0"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("indexed", sa.Integer(), server_default="0"),
        sa.Column("mime_type", sa.String(64), server_default="application/pdf"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_documents_sha256", "ai_documents", ["sha256"])
    op.create_index("idx_ai_documents_session", "ai_documents", ["session_id"])

    # 2. ai_processing_jobs
    op.create_table(
        "ai_processing_jobs",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("ai_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_stage", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # 3. ai_financial_metrics
    op.create_table(
        "ai_financial_metrics",
        sa.Column("metric_id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("ai_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_type", sa.String(32), server_default="ANNUAL"),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("statement_type", sa.String(64), nullable=False),
        sa.Column("metric_name", sa.String(64), nullable=False),
        sa.Column("source_label", sa.String(255), nullable=True),
        sa.Column("numeric_value", sa.Numeric(24, 4), nullable=False),
        sa.Column("currency", sa.String(16), server_default="INR"),
        sa.Column("unit", sa.String(32), server_default="CRORES"),
        sa.Column("is_calculated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("formula", sa.Text(), nullable=True),
        sa.Column("is_consolidated", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_metrics_doc", "ai_financial_metrics", ["document_id"])

    # 4. ai_metric_evidence
    op.create_table(
        "ai_metric_evidence",
        sa.Column("evidence_id", sa.String(64), primary_key=True),
        sa.Column("metric_id", sa.String(64), sa.ForeignKey("ai_financial_metrics.metric_id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("ai_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("exact_quote", sa.Text(), nullable=False),
        sa.Column("table_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # 5. ai_red_flag_findings
    op.create_table(
        "ai_red_flag_findings",
        sa.Column("finding_id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("ai_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detection_method", sa.String(32), server_default="RULE_BASED"),
        sa.Column("supporting_evidence", sa.Text(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("requires_review", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_red_flags_doc", "ai_red_flag_findings", ["document_id"])

    # 6. ai_agent_runs
    op.create_table(
        "ai_agent_runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("ai_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ai_agent_runs")
    op.drop_table("ai_red_flag_findings")
    op.drop_table("ai_metric_evidence")
    op.drop_table("ai_financial_metrics")
    op.drop_table("ai_processing_jobs")
    op.drop_table("ai_documents")

