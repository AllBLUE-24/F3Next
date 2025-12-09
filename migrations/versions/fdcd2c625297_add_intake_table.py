"""add intake table

Revision ID: fdcd2c625297
Revises: 0051dd8dcd55
Create Date: 2025-12-07 14:09:52.210971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdcd2c625297'
down_revision: Union[str, Sequence[str], None] = '0051dd8dcd55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    """Create intake table (one row per project, questions as columns)."""
    op.create_table(
        "intake",
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("q1_business_model", sa.Text(), nullable=False),
        sa.Column("q2_annual_turnover", sa.Text(), nullable=False),
        sa.Column("q3_costing_method", sa.Text(), nullable=False),
        sa.Column("q4_inventory_value", sa.Text(), nullable=False),
        sa.Column("q5_bom_handling", sa.Text(), nullable=False),
        sa.Column("q6_line_stoppages", sa.Text(), nullable=False),
        sa.Column("q7_invoice_vs_payment_owners", sa.Text(), nullable=False),
        sa.Column("q8_return_rate", sa.Text(), nullable=False),
        sa.Column("q9_bus_factor_store_manager", sa.Text(), nullable=False),
        sa.Column("q10_dream_fix", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Primary key on project_id already creates an index implicitly.


def downgrade() -> None:
    """Drop intake table."""
    op.drop_table("intake")