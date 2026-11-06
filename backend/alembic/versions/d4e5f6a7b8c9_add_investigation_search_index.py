"""add_investigation_search_index

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-05 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.create_table(
        'investigation_search_index',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investigation_search_index_id'), 'investigation_search_index', ['id'], unique=False)
    op.create_index(op.f('ix_investigation_search_index_investigation_id'), 'investigation_search_index', ['investigation_id'], unique=False)
    op.create_index(op.f('ix_investigation_search_index_source_type'), 'investigation_search_index', ['source_type'], unique=False)
    op.create_index(op.f('ix_investigation_search_index_evidence_id'), 'investigation_search_index', ['evidence_id'], unique=False)
    op.create_index('ix_investigation_search_inv_type', 'investigation_search_index', ['investigation_id', 'source_type'], unique=False)

    if is_postgres:
        # Add tsvector column and GIN index for high-performance PostgreSQL full-text retrieval
        op.add_column('investigation_search_index', sa.Column('tsv', postgresql.TSVECTOR(), nullable=True))
        op.create_index(
            'ix_investigation_search_index_tsv',
            'investigation_search_index',
            ['tsv'],
            postgresql_using='gin'
        )
        # Automatic trigger keeping tsv column synchronized with snippet text
        op.execute("""
            CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
            ON investigation_search_index FOR EACH ROW
            EXECUTE FUNCTION tsvector_update_trigger(tsv, 'pg_catalog.english', snippet);
        """)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP TRIGGER IF EXISTS tsvectorupdate ON investigation_search_index;")
        op.drop_index('ix_investigation_search_index_tsv', table_name='investigation_search_index', postgresql_using='gin')

    op.drop_index('ix_investigation_search_inv_type', table_name='investigation_search_index')
    op.drop_index(op.f('ix_investigation_search_index_evidence_id'), table_name='investigation_search_index')
    op.drop_index(op.f('ix_investigation_search_index_source_type'), table_name='investigation_search_index')
    op.drop_index(op.f('ix_investigation_search_index_investigation_id'), table_name='investigation_search_index')
    op.drop_index(op.f('ix_investigation_search_index_id'), table_name='investigation_search_index')
    op.drop_table('investigation_search_index')

