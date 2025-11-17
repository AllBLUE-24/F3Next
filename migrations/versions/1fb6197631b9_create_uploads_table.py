"""create_uploads_table

Revision ID: 1fb6197631b9
Revises: 50e147cee8ef
Create Date: 2025-11-16 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision: str = "1fb6197631b9"
down_revision: Union[str, Sequence[str], None] = "50e147cee8ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create uploads table."""
    op.create_table(
        "uploads",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("s3_url", sa.Text, nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column(
            "status",
            # reference existing upload_status enum by name; do NOT create it here
            pg.ENUM(
                "uploaded",
                "validating",
                "validated",
                "failed",
                name="upload_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'uploaded'::upload_status"),
        ),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    """Drop uploads table."""
    op.drop_table("uploads")
