"""add_node_engine_and_answers

Revision ID: d64619abf512
Revises: 1429182024d1
Create Date: 2025-12-20 01:06:35.255453

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd64619abf512'
down_revision: Union[str, Sequence[str], None] = '1429182024d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================
    # 1. MASTER NODE LIBRARY
    # =========================================================
    op.create_table(
        "node_bank",
        sa.Column("node_id", sa.String(length=50), primary_key=True),
        sa.Column("module_ref", sa.String(length=20), nullable=False),
        sa.Column("target_role", sa.String(length=20), nullable=False),
        sa.Column("node_data", postgresql.JSONB, nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Performance indexes
    op.create_index("idx_nodes_module", "node_bank", ["module_ref"])
    op.create_index("idx_nodes_role", "node_bank", ["target_role"])
    op.create_index(
        "idx_nodes_tags",
        "node_bank",
        [sa.text("(node_data -> 'logic_gates' -> 'required_tags')")],
        postgresql_using="gin",
    )

    # =========================================================
    # 2. PROJECT CONTEXT TAGS (RAM OF THE SYSTEM)
    # =========================================================
    op.add_column(
        "projects",
        sa.Column(
            "context_tags",
            postgresql.JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_project_tags",
        "projects",
        ["context_tags"],
        postgresql_using="gin",
    )

    # =========================================================
    # 3. PROJECT ANSWERS (ANSWER + CONSEQUENCE SNAPSHOT)
    # =========================================================
    op.create_table(
        "project_answers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),  # matches your current projects.id strategy
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_id",
            sa.String(length=50),
            sa.ForeignKey("node_bank.node_id"),
            nullable=False,
        ),
        sa.Column("user_role", sa.String(length=20)),
        sa.Column("answer_value", postgresql.JSONB, nullable=False),
        sa.Column("tags_injected", postgresql.JSONB),
        sa.Column("payload_impact", postgresql.JSONB),
        sa.Column("answered_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("project_id", "node_id", name="uq_project_node_answer"),
    )


def downgrade() -> None:
    # Reverse order (dependencies matter)
    op.drop_table("project_answers")

    op.drop_index("idx_project_tags", table_name="projects")
    op.drop_column("projects", "context_tags")

    op.drop_index("idx_nodes_tags", table_name="node_bank")
    op.drop_index("idx_nodes_role", table_name="node_bank")
    op.drop_index("idx_nodes_module", table_name="node_bank")
    op.drop_table("node_bank")