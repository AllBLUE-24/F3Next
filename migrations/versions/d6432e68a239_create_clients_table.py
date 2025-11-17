"""create clients table

Revision ID: d6432e68a239
Revises: 8d79722395ab
Create Date: 2025-11-16 23:46:27.196162

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6432e68a239'
down_revision: Union[str, Sequence[str], None] = '8d79722395ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    op.create_table(
        "clients",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("firebase_uid", sa.Text(), unique=True),
        sa.Column("email", sa.Text(), unique=True),
        sa.Column("company_name", sa.Text()),
        sa.Column("contact_person", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("clients")