"""add admission calendar event details

Revision ID: 20260718_0003
Revises: 20260718_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0003"
down_revision: str | None = "20260718_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("admission_events", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("event_type", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("start_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("end_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("application_url", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("is_estimated", sa.Boolean(), nullable=True))
        batch_op.add_column(
            sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True)
        )
    if op.get_bind().dialect.name == "sqlite":
        op.execute("UPDATE admission_events SET start_at = event_date || ' 00:00:00.000000'")
    else:
        op.execute(
            "UPDATE admission_events SET start_at = event_date::timestamp AT TIME ZONE 'UTC'"
        )
    op.execute("UPDATE admission_events SET event_type = 'schedule', is_estimated = true")
    op.execute("UPDATE admission_events SET last_verified_at = source_checked_at")
    with op.batch_alter_table("admission_events", recreate="always") as batch_op:
        batch_op.alter_column("event_type", nullable=False)
        batch_op.alter_column("start_at", nullable=False)
        batch_op.alter_column("is_estimated", nullable=False)
        batch_op.drop_column("event_date")
        batch_op.drop_column("source_checked_at")
        batch_op.create_index("ix_admission_events_event_type", ["event_type"])
        batch_op.create_index("ix_admission_events_start_at", ["start_at"])


def downgrade() -> None:
    with op.batch_alter_table("admission_events", recreate="always") as batch_op:
        batch_op.drop_index("ix_admission_events_start_at")
        batch_op.drop_index("ix_admission_events_event_type")
        batch_op.add_column(sa.Column("event_date", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("source_checked_at", sa.DateTime(timezone=True), nullable=True)
        )
    op.execute("UPDATE admission_events SET event_date = date(start_at)")
    op.execute("UPDATE admission_events SET source_checked_at = last_verified_at")
    with op.batch_alter_table("admission_events", recreate="always") as batch_op:
        batch_op.alter_column("event_date", nullable=False)
        batch_op.alter_column("source_checked_at", nullable=False)
        batch_op.drop_column("last_verified_at")
        batch_op.drop_column("is_estimated")
        batch_op.drop_column("description")
        batch_op.drop_column("application_url")
        batch_op.drop_column("end_at")
        batch_op.drop_column("start_at")
        batch_op.drop_column("event_type")
