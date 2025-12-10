"""update enums of project_status

Revision ID: 519f0958c079
Revises: fe1d183a6a5c
Create Date: 2025-12-10 15:41:39.574891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '519f0958c079'
down_revision: Union[str, Sequence[str], None] = 'fe1d183a6a5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new values to existing ENUM type (safe)
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'interested';")
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'listed';")
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'paid';")
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'hook_completed';")


def downgrade() -> None:
    # PostgreSQL does NOT allow removing enum values easily.
    # So we document downgrade as NOOP.
    pass
