"""create project status enum

Revision ID: 344f2e0f65f3
Revises: 
Create Date: 2025-11-16 23:46:05.069641

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '344f2e0f65f3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_status') THEN
                CREATE TYPE project_status AS ENUM (
                    'created',
                    'discovery_complete',
                    'templates_ready',
                    'uploaded',
                    'validated'
                );
            END IF;
        END$$;
        """
    )

def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS project_status CASCADE;")
