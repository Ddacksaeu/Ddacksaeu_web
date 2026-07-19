"""allow same-named professors in separate departments

Revision ID: 20260719_0006
Revises: 20260719_0005
"""

from alembic import op

revision = "20260719_0006"
down_revision = "20260719_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("professors", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_professors_university_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_professors_university_department_name", ["university_id", "department_id", "name"]
        )


def downgrade() -> None:
    with op.batch_alter_table("professors", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_professors_university_department_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_professors_university_name", ["university_id", "name"]
        )
