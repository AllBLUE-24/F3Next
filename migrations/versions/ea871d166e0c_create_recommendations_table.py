"""create recommendations table

Revision ID: ea871d166e0c
Revises: 6b6bfe2f55f6
Create Date: 2025-11-16 23:50:25.410851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea871d166e0c'
down_revision: Union[str, Sequence[str], None] = '6b6bfe2f55f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "recommendations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("agent_run_id", sa.UUID()),
        sa.Column("erp_choice", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("modules", sa.JSON(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_recommendations_project_id", "recommendations", ["project_id"])


def downgrade():
    op.drop_index("ix_recommendations_project_id", table_name="recommendations")
    op.drop_table("recommendations")