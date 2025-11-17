"""create upload status enum

Revision ID: 8d79722395ab
Revises: 344f2e0f65f3
Create Date: 2025-11-16 23:46:21.302903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d79722395ab'
down_revision: Union[str, Sequence[str], None] = '344f2e0f65f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'upload_status') THEN
                CREATE TYPE upload_status AS ENUM (
                    'uploaded',
                    'validating',
                    'validated',
                    'failed'
                );
            END IF;
        END$$;
        """
    )

def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS upload_status CASCADE;")
