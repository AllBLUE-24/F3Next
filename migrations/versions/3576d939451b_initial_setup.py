"""initial_setup

Revision ID: 3576d939451b
Revises: 
Create Date: 2025-12-25 07:37:46.780882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3576d939451b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


"""baseline schema

Revision ID: 0001_baseline
Revises: 
Create Date: 2025-XX-XX
"""



def upgrade():
    # ---------- ENUMS ----------
    project_status_enum = postgresql.ENUM(
        "interested",
        "listed",
        "paid",
        "hook_completed",
        name="project_status",
    )
    project_status_enum.create(op.get_bind(), checkfirst=True)

    # ---------- CLIENTS ----------
    op.create_table(
        "clients",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("email", sa.Text, unique=True, index=True),
        sa.Column("full_name", sa.Text),
        sa.Column("role", sa.Text),
        sa.Column("company_name", sa.Text),
        sa.Column("status", sa.Text),
        sa.Column("phone_no", sa.Text),
        sa.Column("whatsapp_no", sa.Text),
        sa.Column("silver_bullet", sa.Text),
        sa.Column("comment", sa.Text),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # ---------- PROJECTS ----------
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", sa.Text, sa.ForeignKey("clients.id", ondelete="CASCADE")),
        sa.Column("status", sa.Enum(name="project_status"), server_default="interested"),
        sa.Column("company_name", sa.Text),
        sa.Column("plan", sa.Text),
        sa.Column("transaction_id", sa.Text),
        sa.Column("context_tags", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("ix_projects_client_id", "projects", ["client_id"])
    op.create_index("ix_projects_context_tags", "projects", ["context_tags"], postgresql_using="gin")

    # ---------- HOOKS ----------
    op.create_table(
        "hooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("answers_health_check", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("ix_hooks_project_id", "hooks", ["project_id"])

    # ---------- NODE BANK ----------
    op.create_table(
        "node_bank",
        sa.Column("node_id", sa.Text, primary_key=True),
        sa.Column("module_ref", sa.Text, nullable=False),
        sa.Column("target_role", sa.Text, nullable=False),
        sa.Column("node_data", postgresql.JSONB, nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("ix_node_bank_module_ref", "node_bank", ["module_ref"])
    op.create_index("ix_node_bank_target_role", "node_bank", ["target_role"])
    op.create_index(
        "ix_node_bank_logic_gates",
        "node_bank",
        [sa.text("(node_data -> 'logic_gates')")],
        postgresql_using="gin",
    )


def downgrade():
    op.drop_table("hooks")
    op.drop_table("node_bank")
    op.drop_table("projects")
    op.drop_table("clients")

    project_status_enum = postgresql.ENUM(name="project_status")
    project_status_enum.drop(op.get_bind(), checkfirst=True)

    # ### end Alembic commands ###
