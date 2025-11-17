"""create events table

Revision ID: 5b1f92ca7b53
Revises: bed0848ac776
Create Date: 2025-11-16 23:50:59.795204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b1f92ca7b53'
down_revision: Union[str, Sequence[str], None] = 'bed0848ac776'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text()),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_events_project_id", "events", ["project_id"])


def downgrade():
    op.drop_index("ix_events_project_id", table_name="events")
    op.drop_table("events")
