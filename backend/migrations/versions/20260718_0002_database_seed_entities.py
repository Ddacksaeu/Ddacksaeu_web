"""add normalized database and fixture-seed entities

Revision ID: 20260718_0002
Revises: 20260718_0001
Create Date: 2026-07-18 00:30:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0002"
down_revision: str | None = "20260718_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "universities",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country", sa.String(80), nullable=False),
        sa.Column("source_url", sa.String(500)),
        sa.Column("source_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "departments",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("university_id", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("university_id", "name", name="uq_departments_university_name"),
    )
    op.create_index("ix_departments_university_id", "departments", ["university_id"])
    op.create_table(
        "professors",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("university_id", sa.String(120), nullable=False),
        sa.Column("department_id", sa.String(120), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("profile_url", sa.String(500)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("source_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("university_id", "name", name="uq_professors_university_name"),
    )
    op.create_index("ix_professors_department_id", "professors", ["department_id"])
    op.create_index("ix_professors_university_id", "professors", ["university_id"])
    op.create_table(
        "keywords",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("term_ko", sa.String(200), nullable=False),
        sa.Column("term_en", sa.String(200)),
        sa.Column("normalized_term", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_term"),
        sa.UniqueConstraint("term_en"),
        sa.UniqueConstraint("term_ko"),
    )

    legacy_universities = sa.table(
        "universities",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("country", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    legacy_departments = sa.table(
        "departments",
        sa.column("id", sa.String),
        sa.column("university_id", sa.String),
        sa.column("name", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    legacy_professors = sa.table(
        "professors",
        sa.column("id", sa.String),
        sa.column("university_id", sa.String),
        sa.column("department_id", sa.String),
        sa.column("name", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        legacy_universities,
        [
            {
                "id": "migration-legacy-university",
                "name": "Migration Legacy University",
                "country": "ZZ",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    op.bulk_insert(
        legacy_departments,
        [
            {
                "id": "migration-legacy-department",
                "university_id": "migration-legacy-university",
                "name": "Legacy Department",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    op.bulk_insert(
        legacy_professors,
        [
            {
                "id": "migration-legacy-professor",
                "university_id": "migration-legacy-university",
                "department_id": "migration-legacy-department",
                "name": "Legacy Fixture Professor",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    with op.batch_alter_table("labs", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("professor_id", sa.String(120), nullable=True))
    op.execute(
        "UPDATE labs SET professor_id = 'migration-legacy-professor' WHERE professor_id IS NULL"
    )
    with op.batch_alter_table("labs", recreate="always") as batch_op:
        batch_op.alter_column("professor_id", existing_type=sa.String(120), nullable=False)
        batch_op.create_foreign_key(
            "fk_labs_professor_id_professors",
            "professors",
            ["professor_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_labs_professor_id", ["professor_id"])

    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(320), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(500), nullable=True))
        batch_op.create_unique_constraint("uq_users_email", ["email"])
    with op.batch_alter_table("papers", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("abstract", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("external_id", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint("uq_papers_lab_external_id", ["lab_id", "external_id"])

    op.create_table(
        "lab_keywords",
        sa.Column("lab_id", sa.String(120), nullable=False),
        sa.Column("keyword_id", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("lab_id", "keyword_id"),
    )
    op.create_table(
        "user_keywords",
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("keyword_id", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "keyword_id"),
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("lab_id", sa.String(120), nullable=False),
        sa.Column("keyword_score", sa.Integer(), nullable=False),
        sa.Column("semantic_score", sa.Integer(), nullable=False),
        sa.Column("research_score", sa.Integer(), nullable=False),
        sa.Column("preference_score", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "keyword_score BETWEEN 0 AND 100", name="ck_recommendations_keyword_score"
        ),
        sa.CheckConstraint(
            "semantic_score BETWEEN 0 AND 100", name="ck_recommendations_semantic_score"
        ),
        sa.CheckConstraint(
            "research_score BETWEEN 0 AND 100", name="ck_recommendations_research_score"
        ),
        sa.CheckConstraint(
            "preference_score BETWEEN 0 AND 100", name="ck_recommendations_preference_score"
        ),
        sa.CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_recommendations_total_score"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_recommendations_confidence"),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lab_id", name="uq_recommendations_user_lab"),
    )
    op.create_index("ix_recommendations_lab_id", "recommendations", ["lab_id"])
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])
    op.create_table(
        "admission_events",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("university_id", sa.String(120)),
        sa.Column("department_id", sa.String(120)),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("source_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "university_id IS NOT NULL OR department_id IS NOT NULL",
            name="ck_admission_events_owner",
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admission_events_department_id", "admission_events", ["department_id"])
    op.create_index("ix_admission_events_university_id", "admission_events", ["university_id"])
    op.create_table(
        "crawl_sources",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("lab_id", sa.String(120)),
        sa.Column("professor_id", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["professor_id"], ["professors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_url"),
    )
    op.create_index("ix_crawl_sources_lab_id", "crawl_sources", ["lab_id"])
    op.create_index("ix_crawl_sources_professor_id", "crawl_sources", ["professor_id"])
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("saved_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')", name="ck_crawl_runs_status"
        ),
        sa.ForeignKeyConstraint(["source_id"], ["crawl_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_runs_source_id", "crawl_runs", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_crawl_runs_source_id", table_name="crawl_runs")
    op.drop_table("crawl_runs")
    op.drop_index("ix_crawl_sources_professor_id", table_name="crawl_sources")
    op.drop_index("ix_crawl_sources_lab_id", table_name="crawl_sources")
    op.drop_table("crawl_sources")
    op.drop_index("ix_admission_events_university_id", table_name="admission_events")
    op.drop_index("ix_admission_events_department_id", table_name="admission_events")
    op.drop_table("admission_events")
    op.drop_index("ix_recommendations_user_id", table_name="recommendations")
    op.drop_index("ix_recommendations_lab_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_table("user_keywords")
    op.drop_table("lab_keywords")
    with op.batch_alter_table("papers", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_papers_lab_external_id", type_="unique")
        batch_op.drop_column("last_crawled_at")
        batch_op.drop_column("external_id")
        batch_op.drop_column("summary")
        batch_op.drop_column("abstract")
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("email")
    with op.batch_alter_table("labs", recreate="always") as batch_op:
        batch_op.drop_index("ix_labs_professor_id")
        batch_op.drop_constraint("fk_labs_professor_id_professors", type_="foreignkey")
        batch_op.drop_column("professor_id")
    op.drop_table("keywords")
    op.drop_index("ix_professors_university_id", table_name="professors")
    op.drop_index("ix_professors_department_id", table_name="professors")
    op.drop_table("professors")
    op.drop_index("ix_departments_university_id", table_name="departments")
    op.drop_table("departments")
    op.drop_table("universities")
