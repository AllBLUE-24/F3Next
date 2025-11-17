"""create kb docs table

Revision ID: 15e0964d7cf0
Revises: 7dbdacb52b86
Create Date: 2025-11-16 23:50:50.777734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15e0964d7cf0'
down_revision: Union[str, Sequence[str], None] = '7dbdacb52b86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "kb_docs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.Text()),
        sa.Column("s3_key", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("kb_docs")
