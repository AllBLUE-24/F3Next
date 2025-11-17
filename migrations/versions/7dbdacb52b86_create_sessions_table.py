"""create sessions table

Revision ID: 7dbdacb52b86
Revises: 164f0eaab3d1
Create Date: 2025-11-16 23:50:45.327593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dbdacb52b86'
down_revision: Union[str, Sequence[str], None] = '164f0eaab3d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("data", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_sessions_project_id", "sessions", ["project_id"])


def downgrade():
    op.drop_index("ix_sessions_project_id", table_name="sessions")
    op.drop_table("sessions")