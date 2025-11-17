"""create kb chunks table

Revision ID: bed0848ac776
Revises: 15e0964d7cf0
Create Date: 2025-11-16 23:50:55.226821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bed0848ac776'
down_revision: Union[str, Sequence[str], None] = '15e0964d7cf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("doc_id", sa.UUID(), sa.ForeignKey("kb_docs.id", ondelete="CASCADE")),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("qdrant_id", sa.Text()),
        sa.Column("chunk_index", sa.Integer()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("kb_chunks")