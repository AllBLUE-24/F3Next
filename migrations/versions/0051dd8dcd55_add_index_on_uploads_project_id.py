"""add index on uploads.project_id

Revision ID: 0051dd8dcd55
Revises: e603ba7b4072
Create Date: 2025-11-26 10:03:34.911263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0051dd8dcd55'
down_revision: Union[str, Sequence[str], None] = 'e603ba7b4072'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_uploads_project_id",
        "uploads",
        ["project_id"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index("ix_uploads_project_id", table_name="uploads")