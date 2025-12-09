"""add hooks table and project meta

Revision ID: 77fb963e5d54
Revises: fdcd2c625297
Create Date: 2025-12-09 11:30:24.835425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '77fb963e5d54'
down_revision: Union[str, Sequence[str], None] = 'fdcd2c625297'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create hooks table and adjust projects columns."""

    # 1) New table: hooks
    op.create_table(
        "hooks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "answers_health_check",
            postgresql.JSONB,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_hooks_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_hooks"),
    )

    # Index for fast lookups by project
    op.create_index("ix_hooks_project_id", "hooks", ["project_id"], unique=False)

    # 2) Add metadata columns to projects
    op.add_column("projects", sa.Column("company_name", sa.TEXT(), nullable=True))
    op.add_column("projects", sa.Column("plan", sa.TEXT(), nullable=True))
    op.add_column("projects", sa.Column("transaction_id", sa.TEXT(), nullable=True))

    # 3) Drop old intake_data column from projects
    #    (this will delete any existing intake_data – currently safe since DB is empty)
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("intake_data")


def downgrade() -> None:
    """Reverse hooks + project changes."""

    # 1) Add intake_data back on projects
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "intake_data",
                postgresql.JSONB,
                nullable=True,
            )
        )

    # 2) Drop new metadata columns on projects
    op.drop_column("projects", "transaction_id")
    op.drop_column("projects", "plan")
    op.drop_column("projects", "company_name")

    # 3) Drop hooks table + index
    op.drop_index("ix_hooks_project_id", table_name="hooks")
    op.drop_table("hooks")