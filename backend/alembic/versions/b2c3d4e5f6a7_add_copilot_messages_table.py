"""add_copilot_messages_table

Revision ID: b2c3d4e5f6a7
Revises: ae9dda31c187
Create Date: 2026-11-05 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'ae9dda31c187'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create copilot_messages table to persist chat conversation history."""
    op.create_table(
        'copilot_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=True),
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_copilot_messages_id'), 'copilot_messages', ['id'], unique=False)
    op.create_index(op.f('ix_copilot_messages_investigation_id'), 'copilot_messages', ['investigation_id'], unique=False)


def downgrade() -> None:
    """Drop copilot_messages table."""
    op.drop_index(op.f('ix_copilot_messages_investigation_id'), table_name='copilot_messages')
    op.drop_index(op.f('ix_copilot_messages_id'), table_name='copilot_messages')
    op.drop_table('copilot_messages')

