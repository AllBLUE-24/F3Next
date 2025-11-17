"""create_projects_table

Revision ID: 6b6bfe2f55f6
Revises: d6432e68a239
Create Date: 2025-11-16 23:XX:XX.XXXXXX
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision: str = "6b6bfe2f55f6"
down_revision: Union[str, Sequence[str], None] = "d6432e68a239"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create projects table."""
    op.create_table(
        "projects",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            # reference the enum type by name, do NOT create it again here
            pg.ENUM(
                "created",
                "discovery_complete",
                "templates_ready",
                "uploaded",
                "validated",
                name="project_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'created'::project_status"),
        ),
        sa.Column("intake_data", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    """Downgrade schema: drop projects table."""
    op.drop_table("projects")
