"""add_deviation_number_source

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-05 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deviation_number_source column to deviations table."""
    op.add_column(
        'deviations',
        sa.Column('deviation_number_source', sa.String(length=20), server_default='SOURCE', nullable=False)
    )


def downgrade() -> None:
    """Remove deviation_number_source column from deviations table."""
    op.drop_column('deviations', 'deviation_number_source')

