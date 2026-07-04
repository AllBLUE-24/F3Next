"""Add consolidated JSON columns to project_target_structures.

Revision ID: add_project_target_json
Revises: add_project_target
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "add_project_target_json"
down_revision: Union[str, None] = "add_project_target"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_target_structures",
        sa.Column("target_structure_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "project_target_structures",
        sa.Column("mvp_boundary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_target_structures", "mvp_boundary_json")
    op.drop_column("project_target_structures", "target_structure_json")
