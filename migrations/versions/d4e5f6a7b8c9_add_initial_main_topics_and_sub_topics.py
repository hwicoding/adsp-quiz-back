"""add_initial_main_topics_and_sub_topics

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-01-20 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """초기 주요항목 및 세부항목 데이터 추가 (프론트엔드 하드코딩 데이터와 일치)"""
    
    # main_topics 테이블에 초기 데이터 추가
    main_topics_table = sa.table(
        'main_topics',
        sa.column('id', sa.Integer),
        sa.column('subject_id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.String),
    )
    
    # 과목 ID 1 (ADsP) 하위의 주요항목들
    op.bulk_insert(
        main_topics_table,
        [
            # 데이터 이해 과목의 주요항목들
            {'id': 1, 'subject_id': 1, 'name': '데이터의 이해', 'description': '데이터의 이해 관련 주요항목'},
            {'id': 2, 'subject_id': 1, 'name': '데이터의 가치와 미래', 'description': '데이터의 가치와 미래 관련 주요항목'},
            {'id': 3, 'subject_id': 1, 'name': '가치 창조를 위한 데이터 사이언스와 전략 인사이트', 'description': '가치 창조를 위한 데이터 사이언스와 전략 인사이트 관련 주요항목'},
            
            # 데이터분석 기획 과목의 주요항목들
            {'id': 4, 'subject_id': 1, 'name': '데이터분석 기획의 이해', 'description': '데이터분석 기획의 이해 관련 주요항목'},
            {'id': 5, 'subject_id': 1, 'name': '분석 마스터 플랜', 'description': '분석 마스터 플랜 관련 주요항목'},
            
            # 데이터분석 과목의 주요항목들
            {'id': 6, 'subject_id': 1, 'name': 'R기초와 데이터 마트', 'description': 'R기초와 데이터 마트 관련 주요항목'},
            {'id': 7, 'subject_id': 1, 'name': '통계분석', 'description': '통계분석 관련 주요항목'},
            {'id': 8, 'subject_id': 1, 'name': '정형 데이터 마이닝', 'description': '정형 데이터 마이닝 관련 주요항목'},
        ],
    )
    
    # sub_topics 테이블에 초기 데이터 추가
    sub_topics_table = sa.table(
        'sub_topics',
        sa.column('id', sa.Integer),
        sa.column('main_topic_id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('core_content', sa.Text),
    )
    
    op.bulk_insert(
        sub_topics_table,
        [
            # 주요항목 1: 데이터의 이해
            {'id': 1, 'main_topic_id': 1, 'name': '데이터와 정보', 'description': '데이터와 정보 관련 세부항목', 'core_content': None},
            {'id': 2, 'main_topic_id': 1, 'name': '데이터베이스의 정의와 특징', 'description': '데이터베이스의 정의와 특징 관련 세부항목', 'core_content': None},
            {'id': 3, 'main_topic_id': 1, 'name': '데이터베이스 활용', 'description': '데이터베이스 활용 관련 세부항목', 'core_content': None},
            {'id': 4, 'main_topic_id': 1, 'name': '빅데이터의 이해', 'description': '빅데이터의 이해 관련 세부항목', 'core_content': None},
            {'id': 5, 'main_topic_id': 1, 'name': '빅데이터의 가치와 영향', 'description': '빅데이터의 가치와 영향 관련 세부항목', 'core_content': None},
            
            # 주요항목 2: 데이터의 가치와 미래
            {'id': 6, 'main_topic_id': 2, 'name': '비즈니스 모델', 'description': '비즈니스 모델 관련 세부항목', 'core_content': None},
            {'id': 7, 'main_topic_id': 2, 'name': '위기 요인과 통제 방안', 'description': '위기 요인과 통제 방안 관련 세부항목', 'core_content': None},
            {'id': 8, 'main_topic_id': 2, 'name': '미래의 빅데이터', 'description': '미래의 빅데이터 관련 세부항목', 'core_content': None},
            
            # 주요항목 3: 가치 창조를 위한 데이터 사이언스와 전략 인사이트
            {'id': 9, 'main_topic_id': 3, 'name': '빅데이터분석과 전략 인사이트', 'description': '빅데이터분석과 전략 인사이트 관련 세부항목', 'core_content': None},
            {'id': 10, 'main_topic_id': 3, 'name': '전략 인사이트 도출을 위한 필요 역량', 'description': '전략 인사이트 도출을 위한 필요 역량 관련 세부항목', 'core_content': None},
            {'id': 11, 'main_topic_id': 3, 'name': '빅데이터 그리고 데이터 사이언스의 미래', 'description': '빅데이터 그리고 데이터 사이언스의 미래 관련 세부항목', 'core_content': None},
            
            # 주요항목 4: 데이터분석 기획의 이해
            {'id': 12, 'main_topic_id': 4, 'name': '분석 기획 방향성 도출', 'description': '분석 기획 방향성 도출 관련 세부항목', 'core_content': None},
            {'id': 13, 'main_topic_id': 4, 'name': '분석 방법론', 'description': '분석 방법론 관련 세부항목', 'core_content': None},
            {'id': 14, 'main_topic_id': 4, 'name': '분석 과제 발굴', 'description': '분석 과제 발굴 관련 세부항목', 'core_content': None},
            {'id': 15, 'main_topic_id': 4, 'name': '분석 프로젝트 관리 방안', 'description': '분석 프로젝트 관리 방안 관련 세부항목', 'core_content': None},
            
            # 주요항목 5: 분석 마스터 플랜
            {'id': 16, 'main_topic_id': 5, 'name': '마스터 플랜 수립', 'description': '마스터 플랜 수립 관련 세부항목', 'core_content': None},
            {'id': 17, 'main_topic_id': 5, 'name': '분석 거버넌스 체계 수립', 'description': '분석 거버넌스 체계 수립 관련 세부항목', 'core_content': None},
            
            # 주요항목 6: R기초와 데이터 마트
            {'id': 18, 'main_topic_id': 6, 'name': 'R기초', 'description': 'R기초 관련 세부항목', 'core_content': None},
            {'id': 19, 'main_topic_id': 6, 'name': '데이터 마트', 'description': '데이터 마트 관련 세부항목', 'core_content': None},
            {'id': 20, 'main_topic_id': 6, 'name': '결측값 처리와 이상값 검색', 'description': '결측값 처리와 이상값 검색 관련 세부항목', 'core_content': None},
            
            # 주요항목 7: 통계분석
            {'id': 21, 'main_topic_id': 7, 'name': '통계학 개론', 'description': '통계학 개론 관련 세부항목', 'core_content': None},
            {'id': 22, 'main_topic_id': 7, 'name': '기초 통계분석', 'description': '기초 통계분석 관련 세부항목', 'core_content': None},
            {'id': 23, 'main_topic_id': 7, 'name': '다변량 분석', 'description': '다변량 분석 관련 세부항목', 'core_content': None},
            {'id': 24, 'main_topic_id': 7, 'name': '시계열 예측', 'description': '시계열 예측 관련 세부항목', 'core_content': None},
            
            # 주요항목 8: 정형 데이터 마이닝
            {'id': 25, 'main_topic_id': 8, 'name': '데이터 마이닝 개요', 'description': '데이터 마이닝 개요 관련 세부항목', 'core_content': None},
            {'id': 26, 'main_topic_id': 8, 'name': '분류분석(Classification)', 'description': '분류분석(Classification) 관련 세부항목', 'core_content': None},
            {'id': 27, 'main_topic_id': 8, 'name': '군집분석(Clustering)', 'description': '군집분석(Clustering) 관련 세부항목', 'core_content': None},
            {'id': 28, 'main_topic_id': 8, 'name': '연관분석(Association Analysis)', 'description': '연관분석(Association Analysis) 관련 세부항목', 'core_content': None},
        ],
    )


def downgrade() -> None:
    """초기 데이터 삭제"""
    op.execute("DELETE FROM sub_topics")
    op.execute("DELETE FROM main_topics")
