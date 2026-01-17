"""add_initial_subjects

Revision ID: 2f68a60ba812
Revises: c7e2f1fcdf79
Create Date: 2026-01-17 21:59:08.379591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f68a60ba812'
down_revision: Union[str, Sequence[str], None] = 'c7e2f1fcdf79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """초기 과목 데이터 추가"""
    subjects_table = sa.table(
        'subjects',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.String),
    )
    
    op.bulk_insert(
        subjects_table,
        [
            {
                'id': 1,
                'name': 'ADsP',
                'description': '데이터 분석 준전문가 (Advanced Data Analytics Semi-Professional)',
            },
        ],
    )


def downgrade() -> None:
    """초기 과목 데이터 삭제"""
    op.execute("DELETE FROM subjects WHERE id = 1")
