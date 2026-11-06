"""Initial schema with PostgreSQL models and user links

Revision ID: e9e38a07f832
Revises: 
Create Date: 2026-11-04 19:42:15.638268

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e9e38a07f832'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. investigations
    op.create_table(
        'investigations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('stage', sa.String(length=50), nullable=True),
        sa.Column('lead_investigator', sa.String(length=100), nullable=True),
        sa.Column('lead_investigator_id', sa.Integer(), nullable=True),
        sa.Column('qa_approver', sa.String(length=100), nullable=True),
        sa.Column('qa_approver_id', sa.Integer(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=True),
        sa.Column('approval_date', sa.DateTime(), nullable=True),
        sa.Column('approval_comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lead_investigator_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['qa_approver_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investigations_id'), 'investigations', ['id'], unique=False)
    op.create_index(op.f('ix_investigations_investigation_number'), 'investigations', ['investigation_number'], unique=True)

    # 3. deviations
    op.create_table(
        'deviations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('deviation_number', sa.String(length=50), nullable=False),
        sa.Column('deviation_type', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('batch_number', sa.String(length=100), nullable=False),
        sa.Column('product_name', sa.String(length=200), nullable=False),
        sa.Column('unit_operation', sa.String(length=100), nullable=True),
        sa.Column('equipment_id', sa.String(length=100), nullable=True),
        sa.Column('bpr_number', sa.String(length=100), nullable=True),
        sa.Column('target_yield_kg', sa.Float(), nullable=True),
        sa.Column('actual_yield_kg', sa.Float(), nullable=True),
        sa.Column('occurrence_datetime', sa.DateTime(), nullable=True),
        sa.Column('detection_datetime', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('immediate_containment', sa.Text(), nullable=True),
        sa.Column('is_ai_populated', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deviations_id'), 'deviations', ['id'], unique=False)
    op.create_index(op.f('ix_deviations_deviation_number'), 'deviations', ['deviation_number'], unique=False)
    op.create_index(op.f('ix_deviations_batch_number'), 'deviations', ['batch_number'], unique=False)

    # 4. evidences
    op.create_table(
        'evidences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verified_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidences_id'), 'evidences', ['id'], unique=False)

    # 5. investigation_findings
    op.create_table(
        'investigation_findings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('finding_text', sa.Text(), nullable=False),
        sa.Column('finding_type', sa.String(length=50), nullable=True),
        sa.Column('evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('is_ai_suggested', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investigation_findings_id'), 'investigation_findings', ['id'], unique=False)

    # 6. five_whys_steps
    op.create_table(
        'five_whys_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('question', sa.String(length=500), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('is_ai_suggested', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_five_whys_steps_id'), 'five_whys_steps', ['id'], unique=False)

    # 7. fishbone_causes
    op.create_table(
        'fishbone_causes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('cause_description', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('is_ai_suggested', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fishbone_causes_id'), 'fishbone_causes', ['id'], unique=False)

    # 8. root_causes
    op.create_table(
        'root_causes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('cause_statement', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('evidence_summary', sa.Text(), nullable=True),
        sa.Column('is_ai_suggested', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('investigator_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_root_causes_id'), 'root_causes', ['id'], unique=False)

    # 9. capa_actions
    op.create_table(
        'capa_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('root_cause_id', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('owner', sa.String(length=100), nullable=True),
        sa.Column('deadline', sa.String(length=50), nullable=True),
        sa.Column('effectiveness_criteria', sa.Text(), nullable=True),
        sa.Column('effectiveness_review_period_days', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('is_ai_suggested', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['root_cause_id'], ['root_causes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capa_actions_id'), 'capa_actions', ['id'], unique=False)

    # 10. ai_interactions
    op.create_table(
        'ai_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),
        sa.Column('prompt_summary', sa.Text(), nullable=True),
        sa.Column('response_data', sa.Text(), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_interactions_id'), 'ai_interactions', ['id'], unique=False)

    # 11. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_name', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=50), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)

def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('ai_interactions')
    op.drop_table('capa_actions')
    op.drop_table('root_causes')
    op.drop_table('fishbone_causes')
    op.drop_table('five_whys_steps')
    op.drop_table('investigation_findings')
    op.drop_table('evidences')
    op.drop_table('deviations')
    op.drop_table('investigations')
    op.drop_table('users')
