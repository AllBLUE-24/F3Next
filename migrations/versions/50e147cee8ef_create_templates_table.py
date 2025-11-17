"""create templates table

Revision ID: 50e147cee8ef
Revises: ea871d166e0c
Create Date: 2025-11-16 23:50:30.444128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50e147cee8ef'
down_revision: Union[str, Sequence[str], None] = 'ea871d166e0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text()),
        sa.Column("schema_json", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_templates_project_id", "templates", ["project_id"])


def downgrade():
    op.drop_index("ix_templates_project_id", table_name="templates")
    op.drop_table("templates")
