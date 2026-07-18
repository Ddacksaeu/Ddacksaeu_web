"""initial MVP schema

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "labs",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("professor_name", sa.String(length=120), nullable=False),
        sa.Column("department", sa.String(length=200), nullable=False),
        sa.Column("field", sa.String(length=120), nullable=False),
        sa.Column("homepage_url", sa.String(length=500)),
        sa.Column("location", sa.String(length=200)),
        sa.Column("contact_email", sa.String(length=320)),
        sa.Column("summary_text", sa.Text()),
        sa.Column("summary_origin", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=500)),
        sa.Column("source_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("affiliation", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("program", sa.String(length=120), nullable=False),
        sa.Column("interests_json", sa.JSON(), nullable=False),
        sa.Column("skills_json", sa.JSON(), nullable=False),
        sa.Column("methodologies_json", sa.JSON(), nullable=False),
        sa.Column("projects_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "lab_facts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lab_id", sa.String(length=120), nullable=False),
        sa.Column("fact_type", sa.String(length=32), nullable=False),
        sa.Column("value_text", sa.Text()),
        sa.Column("value_number", sa.Integer()),
        sa.Column("audience", sa.String(length=32)),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=500)),
        sa.Column("source_checked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_facts_lab_id", "lab_facts", ["lab_id"])
    op.create_table(
        "papers",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("lab_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("venue", sa.String(length=200), nullable=False),
        sa.Column("published_year", sa.Integer(), nullable=False),
        sa.Column("keywords_json", sa.JSON(), nullable=False),
        sa.Column("paper_url", sa.String(length=500)),
        sa.Column("source_url", sa.String(length=500)),
        sa.Column("source_checked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_papers_lab_id", "papers", ["lab_id"])
    op.create_table(
        "favorites",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("lab_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "lab_id"),
    )
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("memo", sa.Text()),
        sa.Column("lab_id", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendar_events_user_id", "calendar_events", ["user_id"])
    op.create_table(
        "uploaded_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_uploaded_documents_user_id", "uploaded_documents", ["user_id"])
    op.create_table(
        "document_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("keywords_json", sa.JSON(), nullable=False),
        sa.Column("skills_json", sa.JSON(), nullable=False),
        sa.Column("methodologies_json", sa.JSON(), nullable=False),
        sa.Column("projects_json", sa.JSON(), nullable=False),
        sa.Column("completeness", sa.Integer()),
        sa.Column("analysis_origin", sa.String(length=32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(length=100)),
        sa.ForeignKeyConstraint(["document_id"], ["uploaded_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_analyses_document_id", "document_analyses", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_document_analyses_document_id", table_name="document_analyses")
    op.drop_table("document_analyses")
    op.drop_index("ix_uploaded_documents_user_id", table_name="uploaded_documents")
    op.drop_table("uploaded_documents")
    op.drop_index("ix_calendar_events_user_id", table_name="calendar_events")
    op.drop_table("calendar_events")
    op.drop_table("favorites")
    op.drop_index("ix_papers_lab_id", table_name="papers")
    op.drop_table("papers")
    op.drop_index("ix_lab_facts_lab_id", table_name="lab_facts")
    op.drop_table("lab_facts")
    op.drop_table("user_profiles")
    op.drop_table("labs")
    op.drop_table("users")
