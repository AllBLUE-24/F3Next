"""create validation reports table

Revision ID: 164f0eaab3d1
Revises: 1fb6197631b9
Create Date: 2025-11-16 23:50:40.024594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '164f0eaab3d1'
down_revision: Union[str, Sequence[str], None] = '1fb6197631b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "validation_reports",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("upload_id", sa.UUID(), sa.ForeignKey("uploads.id", ondelete="CASCADE")),
        sa.Column("error_count", sa.Integer(), server_default="0"),
        sa.Column("warning_count", sa.Integer(), server_default="0"),
        sa.Column("total_records", sa.Integer(), server_default="0"),
        sa.Column("errors", sa.JSON(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("warnings", sa.JSON(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_validation_reports_upload_id", "validation_reports", ["upload_id"])


def downgrade():
    op.drop_index("ix_validation_reports_upload_id", table_name="validation_reports")
    op.drop_table("validation_reports")
