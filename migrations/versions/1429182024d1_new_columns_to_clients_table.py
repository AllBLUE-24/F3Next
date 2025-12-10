"""new columns to clients table

Revision ID: 1429182024d1
Revises: 519f0958c079
Create Date: 2025-12-10 16:01:13.571262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1429182024d1'
down_revision: Union[str, Sequence[str], None] = '519f0958c079'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new nullable columns
    op.add_column("clients", sa.Column("phone_no", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("whatsapp_no", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("silver_bullet", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("comment", sa.Text(), nullable=True))


def downgrade() -> None:
    # Drop the columns in reverse order
    op.drop_column("clients", "comment")
    op.drop_column("clients", "silver_bullet")
    op.drop_column("clients", "whatsapp_no")
    op.drop_column("clients", "phone_no")