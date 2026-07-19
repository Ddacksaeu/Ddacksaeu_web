"""add POSTECH import provenance

Revision ID: 20260719_0005
Revises: 20260719_0004
"""

from alembic import op
import sqlalchemy as sa

revision = "20260719_0005"
down_revision = "20260719_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for table in ("labs", "papers"):
        op.add_column(table, sa.Column("source_type", sa.String(50), nullable=False, server_default="fixture"))
        op.add_column(table, sa.Column("import_batch_id", sa.String(36)))
        op.add_column(table, sa.Column("validation_status", sa.String(32), nullable=False, server_default="valid"))
        op.create_index(f"ix_{table}_import_batch_id", table, ["import_batch_id"])


def downgrade() -> None:
    for table in ("papers", "labs"):
        op.drop_index(f"ix_{table}_import_batch_id", table_name=table)
        op.drop_column(table, "validation_status")
        op.drop_column(table, "import_batch_id")
        op.drop_column(table, "source_type")
    op.drop_table("import_batches")
