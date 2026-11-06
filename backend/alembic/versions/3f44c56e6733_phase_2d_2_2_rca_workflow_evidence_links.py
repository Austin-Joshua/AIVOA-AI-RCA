"""phase_2d_2_2_rca_workflow_evidence_links

Revision ID: 3f44c56e6733
Revises: a1b2c3d4e5f6
Create Date: 2026-11-05 11:30:52.164099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f44c56e6733'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for Phase 2D.2.2 evidence-linked RCA workflow."""
    # 1. five_whys_evidence_links
    op.create_table(
        'five_whys_evidence_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('five_whys_step_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False, server_default='SUPPORTING'),
        sa.Column('relevance_explanation', sa.Text(), nullable=True),
        sa.Column('confidence_rating', sa.String(length=20), nullable=True, server_default='HIGH'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidences.id'], name='fk_five_whys_evidence_links_evidence_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['five_whys_step_id'], ['five_whys_steps.id'], name='fk_five_whys_evidence_links_step_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('five_whys_step_id', 'evidence_id', 'relationship_type', name='uq_five_whys_evidence_rel')
    )
    op.create_index(op.f('ix_five_whys_evidence_links_evidence_id'), 'five_whys_evidence_links', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_five_whys_evidence_links_five_whys_step_id'), 'five_whys_evidence_links', ['five_whys_step_id'], unique=False)
    op.create_index(op.f('ix_five_whys_evidence_links_id'), 'five_whys_evidence_links', ['id'], unique=False)

    # 2. fishbone_evidence_links
    op.create_table(
        'fishbone_evidence_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fishbone_cause_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False, server_default='SUPPORTING'),
        sa.Column('relevance_explanation', sa.Text(), nullable=True),
        sa.Column('confidence_rating', sa.String(length=20), nullable=True, server_default='HIGH'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidences.id'], name='fk_fishbone_evidence_links_evidence_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fishbone_cause_id'], ['fishbone_causes.id'], name='fk_fishbone_evidence_links_cause_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fishbone_cause_id', 'evidence_id', 'relationship_type', name='uq_fishbone_evidence_rel')
    )
    op.create_index(op.f('ix_fishbone_evidence_links_evidence_id'), 'fishbone_evidence_links', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_fishbone_evidence_links_fishbone_cause_id'), 'fishbone_evidence_links', ['fishbone_cause_id'], unique=False)
    op.create_index(op.f('ix_fishbone_evidence_links_id'), 'fishbone_evidence_links', ['id'], unique=False)

    # 3. fishbone_causes additions
    op.add_column('fishbone_causes', sa.Column('verified_by_user_id', sa.Integer(), nullable=True))
    op.add_column('fishbone_causes', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.add_column('fishbone_causes', sa.Column('verification_notes', sa.Text(), nullable=True))
    op.add_column('fishbone_causes', sa.Column('promoted_to_root_cause_id', sa.Integer(), nullable=True))
    op.add_column('fishbone_causes', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_fishbone_causes_investigation_id'), 'fishbone_causes', ['investigation_id'], unique=False)
    op.create_foreign_key('fk_fishbone_causes_promoted_to_root_cause_id', 'fishbone_causes', 'root_causes', ['promoted_to_root_cause_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_fishbone_causes_verified_by_user_id', 'fishbone_causes', 'users', ['verified_by_user_id'], ['id'], ondelete='SET NULL')

    # 4. five_whys_steps additions
    op.add_column('five_whys_steps', sa.Column('verified_by_user_id', sa.Integer(), nullable=True))
    op.add_column('five_whys_steps', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.add_column('five_whys_steps', sa.Column('verification_notes', sa.Text(), nullable=True))
    op.add_column('five_whys_steps', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_five_whys_steps_investigation_id'), 'five_whys_steps', ['investigation_id'], unique=False)
    op.create_foreign_key('fk_five_whys_steps_verified_by_user_id', 'five_whys_steps', 'users', ['verified_by_user_id'], ['id'], ondelete='SET NULL')

    # 5. root_causes additions
    op.add_column('root_causes', sa.Column('source_type', sa.String(length=50), nullable=True, server_default='DIRECT_SYNTHESIS'))
    op.add_column('root_causes', sa.Column('source_id', sa.Integer(), nullable=True))
    op.add_column('root_causes', sa.Column('confirmed_by', sa.String(length=100), nullable=True))
    op.add_column('root_causes', sa.Column('confirmed_by_user_id', sa.Integer(), nullable=True))
    op.add_column('root_causes', sa.Column('confirmed_at', sa.DateTime(), nullable=True))
    op.add_column('root_causes', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('root_causes', sa.Column('rejected_by', sa.String(length=100), nullable=True))
    op.add_column('root_causes', sa.Column('rejected_by_user_id', sa.Integer(), nullable=True))
    op.add_column('root_causes', sa.Column('rejected_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_root_causes_rejected_by_user_id', 'root_causes', 'users', ['rejected_by_user_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_root_causes_confirmed_by_user_id', 'root_causes', 'users', ['confirmed_by_user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_root_causes_confirmed_by_user_id', 'root_causes', type_='foreignkey')
    op.drop_constraint('fk_root_causes_rejected_by_user_id', 'root_causes', type_='foreignkey')
    op.drop_column('root_causes', 'rejected_at')
    op.drop_column('root_causes', 'rejected_by_user_id')
    op.drop_column('root_causes', 'rejected_by')
    op.drop_column('root_causes', 'rejection_reason')
    op.drop_column('root_causes', 'confirmed_at')
    op.drop_column('root_causes', 'confirmed_by_user_id')
    op.drop_column('root_causes', 'confirmed_by')
    op.drop_column('root_causes', 'source_id')
    op.drop_column('root_causes', 'source_type')

    op.drop_constraint('fk_five_whys_steps_verified_by_user_id', 'five_whys_steps', type_='foreignkey')
    op.drop_index(op.f('ix_five_whys_steps_investigation_id'), table_name='five_whys_steps')
    op.drop_column('five_whys_steps', 'updated_at')
    op.drop_column('five_whys_steps', 'verification_notes')
    op.drop_column('five_whys_steps', 'verified_at')
    op.drop_column('five_whys_steps', 'verified_by_user_id')

    op.drop_constraint('fk_fishbone_causes_verified_by_user_id', 'fishbone_causes', type_='foreignkey')
    op.drop_constraint('fk_fishbone_causes_promoted_to_root_cause_id', 'fishbone_causes', type_='foreignkey')
    op.drop_index(op.f('ix_fishbone_causes_investigation_id'), table_name='fishbone_causes')
    op.drop_column('fishbone_causes', 'updated_at')
    op.drop_column('fishbone_causes', 'promoted_to_root_cause_id')
    op.drop_column('fishbone_causes', 'verification_notes')
    op.drop_column('fishbone_causes', 'verified_at')
    op.drop_column('fishbone_causes', 'verified_by_user_id')

    op.drop_index(op.f('ix_fishbone_evidence_links_id'), table_name='fishbone_evidence_links')
    op.drop_index(op.f('ix_fishbone_evidence_links_fishbone_cause_id'), table_name='fishbone_evidence_links')
    op.drop_index(op.f('ix_fishbone_evidence_links_evidence_id'), table_name='fishbone_evidence_links')
    op.drop_table('fishbone_evidence_links')

    op.drop_index(op.f('ix_five_whys_evidence_links_id'), table_name='five_whys_evidence_links')
    op.drop_index(op.f('ix_five_whys_evidence_links_five_whys_step_id'), table_name='five_whys_evidence_links')
    op.drop_index(op.f('ix_five_whys_evidence_links_evidence_id'), table_name='five_whys_evidence_links')
    op.drop_table('five_whys_evidence_links')
