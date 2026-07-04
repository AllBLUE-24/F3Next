"""add project-level target structures

Revision ID: add_project_target
Revises: <PREVIOUS_REVISION>
Create Date: 2026-07-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_project_target'
down_revision: Union[str, None] = None  # TODO: Set to previous migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project_target_structures table
    op.create_table(
        'project_target_structures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('f3iche', sa.String(), nullable=False),
        sa.Column('discovery_bottleneck', sa.Text(), nullable=True),
        sa.Column('llm_enhanced', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('llm_reasoning', sa.Text(), nullable=True),
        sa.Column('total_doctypes', sa.Integer(), nullable=True),
        sa.Column('total_seed_doctypes', sa.Integer(), nullable=True),
        sa.Column('total_setup_steps', sa.Integer(), nullable=True),
        sa.Column('r2_target_path', sa.String(), nullable=True),
        sa.Column('r2_mvp_path', sa.String(), nullable=True),
        sa.Column('seed_doctypes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('required_doctypes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('setup_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('import_phases', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mvp_focus', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deferred_doctypes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('corpus_independent', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('graph_driven', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_target_structures_project_id', 'project_target_structures', ['project_id'], unique=False)

    # Create project_mvp_boundaries table
    op.create_table(
        'project_mvp_boundaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('f3iche', sa.String(), nullable=False),
        sa.Column('primary_bottleneck', sa.Text(), nullable=True),
        sa.Column('functional_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('seed_doctypes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deferred_doctypes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mode', sa.String(), nullable=False, server_default='f3iche_template'),
        sa.Column('llm_enhanced', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('llm_reasoning', sa.Text(), nullable=True),
        sa.Column('r2_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    op.create_index('ix_project_mvp_boundaries_project_id', 'project_mvp_boundaries', ['project_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_project_mvp_boundaries_project_id', table_name='project_mvp_boundaries')
    op.drop_table('project_mvp_boundaries')
    op.drop_index('ix_project_target_structures_project_id', table_name='project_target_structures')
    op.drop_table('project_target_structures')
