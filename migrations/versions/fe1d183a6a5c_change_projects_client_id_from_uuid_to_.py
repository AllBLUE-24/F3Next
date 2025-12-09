"""change projects.client_id from UUID to TEXT

Revision ID: fe1d183a6a5c
Revises: ca840ec77b95
Create Date: 2025-12-09 13:53:37.656240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fe1d183a6a5c'
down_revision: Union[str, Sequence[str], None] = 'ca840ec77b95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop foreign key constraint safely
    op.execute("""
        ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_client_id_clients;
        ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_client_id_fkey;
    """)

    # 2. Convert type UUID → TEXT
    op.alter_column(
        "projects",
        "client_id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.Text(),
        postgresql_using="client_id::text",
        existing_nullable=False,
    )

    # 3. Re-create foreign key (TEXT → TEXT)
    op.create_foreign_key(
        "fk_projects_client_id_clients",
        "projects",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop new FK
    op.execute("""
        ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_client_id_clients;
    """)

    # Revert TEXT → UUID
    op.alter_column(
        "projects",
        "client_id",
        existing_type=sa.Text(),
        type_=postgresql.UUID(as_uuid=True),
        postgresql_using="client_id::uuid",
        existing_nullable=False,
    )

    # Restore old FK
    op.create_foreign_key(
        "fk_projects_client_id_clients",
        "projects",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )
