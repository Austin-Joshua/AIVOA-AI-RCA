"""phase_2d_2_2_2_security_evidence_provenance

Revision ID: ae9dda31c187
Revises: 3f44c56e6733
Create Date: 2026-11-05 12:42:29.781961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae9dda31c187'
down_revision: Union[str, Sequence[str], None] = '3f44c56e6733'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for Phase 2D.2.2.2: Add evidence uploader and reviewer foreign keys."""
    # 1. uploaded_by_user_id on evidences
    op.add_column('evidences', sa.Column('uploaded_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_evidences_uploaded_by_user_id',
        'evidences', 'users',
        ['uploaded_by_user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        op.f('ix_evidences_uploaded_by_user_id'),
        'evidences',
        ['uploaded_by_user_id'],
        unique=False
    )

    # 2. verified_by_user_id on evidences
    op.add_column('evidences', sa.Column('verified_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_evidences_verified_by_user_id',
        'evidences', 'users',
        ['verified_by_user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        op.f('ix_evidences_verified_by_user_id'),
        'evidences',
        ['verified_by_user_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema for Phase 2D.2.2.2."""
    op.drop_constraint('fk_evidences_verified_by_user_id', 'evidences', type_='foreignkey')
    op.drop_index(op.f('ix_evidences_verified_by_user_id'), table_name='evidences')
    op.drop_column('evidences', 'verified_by_user_id')

    op.drop_constraint('fk_evidences_uploaded_by_user_id', 'evidences', type_='foreignkey')
    op.drop_index(op.f('ix_evidences_uploaded_by_user_id'), table_name='evidences')
    op.drop_column('evidences', 'uploaded_by_user_id')
