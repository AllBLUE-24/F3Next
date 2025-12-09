"""describe change

Revision ID: e603ba7b4072
Revises: 126e7b38bf33
Create Date: 2025-11-25 21:31:40.958402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e603ba7b4072'
down_revision: Union[str, Sequence[str], None] = '126e7b38bf33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema (conservative / safe)."""
    # 1) add updated_at on clients (if missing) with server default and NOT NULL
    op.execute("""
    ALTER TABLE clients
      ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now() NOT NULL;
    """)

    # 2) ensure clients.created_at is NOT NULL (if NULLs exist this will fail)
    #    set any NULL created_at rows to now() first to avoid failure.
    op.execute("""
    UPDATE clients SET created_at = now() WHERE created_at IS NULL;
    ALTER TABLE clients ALTER COLUMN created_at SET NOT NULL;
    """)

    # 3) safely drop client fields that models intentionally removed (use IF EXISTS)
    op.execute("ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_email_key;")
    op.execute("ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_firebase_uid_key;")

    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS contact_person;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS metadata;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS company_name;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS firebase_uid;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS email;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS phone;")

    # 4) ensure projects timestamps are NOT NULL (fix existing NULLs first)
    op.execute("""
    UPDATE projects SET created_at = now() WHERE created_at IS NULL;
    UPDATE projects SET updated_at = now() WHERE updated_at IS NULL;
    ALTER TABLE projects ALTER COLUMN created_at SET NOT NULL;
    ALTER TABLE projects ALTER COLUMN updated_at SET NOT NULL;
    """)

    # 5) create index on projects.client_id if it doesn't already exist
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_projects_client_id ON projects (client_id);
    """)


def downgrade() -> None:
    """Downgrade schema (best-effort)."""
    # 1) drop ix_projects_client_id if exists
    op.execute("DROP INDEX IF EXISTS ix_projects_client_id;")

    # 2) revert projects timestamps to nullable
    op.execute("""
    ALTER TABLE projects ALTER COLUMN updated_at DROP NOT NULL;
    ALTER TABLE projects ALTER COLUMN created_at DROP NOT NULL;
    """)

    # 3) re-add client columns (best-effort: add only if not exists)
    #    types and defaults approximated based on prior migrations
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS phone text;")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS email text;")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS firebase_uid text;")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS company_name text;")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS contact_person text;")

    # 4) re-create unique constraints only if they do not exist
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'clients_firebase_uid_key'
      ) THEN
        ALTER TABLE clients ADD CONSTRAINT clients_firebase_uid_key UNIQUE (firebase_uid);
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'clients_email_key'
      ) THEN
        ALTER TABLE clients ADD CONSTRAINT clients_email_key UNIQUE (email);
      END IF;
    END$$;
    """)

    # 5) drop updated_at column on clients if present
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS updated_at;")

    # 6) allow created_at on clients to be NULL again
    op.execute("ALTER TABLE clients ALTER COLUMN created_at DROP NOT NULL;")
