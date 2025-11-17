"""create audit log table

Revision ID: 126e7b38bf33
Revises: 5b1f92ca7b53
Create Date: 2025-11-16 23:51:04.153142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '126e7b38bf33'
down_revision: Union[str, Sequence[str], None] = '5b1f92ca7b53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_id", sa.UUID()),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("changed_by", sa.Text()),
        sa.Column("old_value", sa.JSON()),
        sa.Column("new_value", sa.JSON()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_log_object", "audit_log", ["object_type", "object_id"])


def downgrade():
    op.drop_index("ix_audit_log_object", table_name="audit_log")
    op.drop_table("audit_log")