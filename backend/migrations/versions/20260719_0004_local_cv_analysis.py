"""store local CV analysis payloads

Revision ID: 20260719_0004
Revises: 20260718_0003
"""

from alembic import op
import sqlalchemy as sa

revision = "20260719_0004"
down_revision = "20260718_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_analyses", sa.Column("structured_analysis_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("document_analyses", sa.Column("search_text", sa.Text(), nullable=False, server_default=""))
    op.add_column("document_analyses", sa.Column("warnings_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    op.drop_column("document_analyses", "warnings_json")
    op.drop_column("document_analyses", "search_text")
    op.drop_column("document_analyses", "structured_analysis_json")
