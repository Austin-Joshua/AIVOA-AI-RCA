"""add_finding_reviewer_metadata

Revision ID: a1b2c3d4e5f6
Revises: 98ea1c729df4
Create Date: 2026-11-05 02:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '98ea1c729df4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add reviewer attribution and acceptance tracking on investigation_findings."""
    op.add_column('investigation_findings', sa.Column('reviewed_by_id', sa.Integer(), nullable=True))
    op.add_column('investigation_findings', sa.Column('is_accepted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('investigation_findings', sa.Column('user_edited', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('investigation_findings', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('investigation_findings', sa.Column('original_finding_text', sa.Text(), nullable=True))
    op.create_index(op.f('ix_investigation_findings_reviewed_by_id'), 'investigation_findings', ['reviewed_by_id'], unique=False)
    op.create_foreign_key('fk_investigation_findings_reviewed_by_id_users', 'investigation_findings', 'users', ['reviewed_by_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_investigation_findings_reviewed_by_id_users', 'investigation_findings', type_='foreignkey')
    op.drop_index(op.f('ix_investigation_findings_reviewed_by_id'), table_name='investigation_findings')
    op.drop_column('investigation_findings', 'original_finding_text')
    op.drop_column('investigation_findings', 'reviewed_at')
    op.drop_column('investigation_findings', 'user_edited')
    op.drop_column('investigation_findings', 'is_accepted')
    op.drop_column('investigation_findings', 'reviewed_by_id')

