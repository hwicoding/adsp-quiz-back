"""add_quiz_validation_table

Revision ID: 97367266b36e
Revises: e8f9a0b1c2d3
Create Date: 2026-01-23 19:32:51.183226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '97367266b36e'
down_revision: Union[str, Sequence[str], None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """quiz_validations 테이블 생성"""
    op.create_table(
        'quiz_validations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('validation_status', sa.String(), nullable=False),
        sa.Column('validation_score', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_quiz_validations_quiz_id'), 'quiz_validations', ['quiz_id'], unique=False)
    op.create_index(op.f('ix_quiz_validations_validation_status'), 'quiz_validations', ['validation_status'], unique=False)
    op.create_index('ix_quiz_validations_latest', 'quiz_validations', ['quiz_id', 'validated_at'], unique=False)


def downgrade() -> None:
    """quiz_validations 테이블 제거"""
    op.drop_index('ix_quiz_validations_latest', table_name='quiz_validations')
    op.drop_index(op.f('ix_quiz_validations_validation_status'), table_name='quiz_validations')
    op.drop_index(op.f('ix_quiz_validations_quiz_id'), table_name='quiz_validations')
    op.drop_table('quiz_validations')
