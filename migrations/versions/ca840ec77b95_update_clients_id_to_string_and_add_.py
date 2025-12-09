"""update clients id to string and add profile fields

Revision ID: ca840ec77b95
Revises: 77fb963e5d54
Create Date: 2025-12-09 13:09:42.116693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ca840ec77b95'
down_revision: Union[str, Sequence[str], None] = '77fb963e5d54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema: change clients.id to TEXT, projects.client_id to TEXT,
    recreate FK, and add profile fields to clients.
    """

    # 1. Drop the existing FK from projects.client_id -> clients.id (whatever its name is)
    # Some DBs may use Alembic's name, others Postgres default name.
    op.execute(
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_client_id_clients;"
    )
    op.execute(
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_client_id_fkey;"
    )

    # 2. Change clients.id UUID -> TEXT
    op.alter_column(
        "clients",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.Text(),
        existing_nullable=False,
        postgresql_using="id::text",
    )

    # 3. Change projects.client_id UUID -> TEXT
    op.alter_column(
        "projects",
        "client_id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.Text(),
        existing_nullable=False,
        postgresql_using="client_id::text",
    )

    # 4. Recreate FK with TEXT types
    op.create_foreign_key(
        "fk_projects_client_id_clients",
        "projects",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Add new profile columns to clients
    op.add_column("clients", sa.Column("full_name", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("company_name", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("role", sa.Text(), nullable=True))

    op.add_column("clients", sa.Column("email", sa.Text(), nullable=True))
    op.add_column(
        "clients",
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    op.add_column(
        "clients",
        sa.Column(
            "last_login_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Reverse the changes: drop new columns, revert TEXT back to UUID, restore FK."""

    # 1. Drop new columns
    op.drop_column("clients", "last_login_at")
    op.drop_column("clients", "status")
    op.drop_column("clients", "email")
    op.drop_column("clients", "role")
    op.drop_column("clients", "company_name")
    op.drop_column("clients", "full_name")

    # 2. Drop FK so we can change types back (defensive, in case name differs)
    op.execute(
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_client_id_clients;"
    )
    op.execute(
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_client_id_fkey;"
    )

    # 3. Change projects.client_id TEXT -> UUID
    op.alter_column(
        "projects",
        "client_id",
        existing_type=sa.Text(),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="client_id::uuid",
    )

    # 4. Change clients.id TEXT -> UUID
    op.alter_column(
        "clients",
        "id",
        existing_type=sa.Text(),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="id::uuid",
    )

    # 5. Recreate FK with UUID types
    op.create_foreign_key(
        "fk_projects_client_id_clients",
        "projects",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )
