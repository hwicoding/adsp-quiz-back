from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz import Quiz
from app.models.subject import Subject


async def get_subject_by_id(session: AsyncSession, subject_id: int) -> Subject | None:
    """ID로 과목 조회"""
    result = await session.execute(select(Subject).where(Subject.id == subject_id))
    return result.scalar_one_or_none()


async def get_all_subjects(session: AsyncSession) -> Sequence[Subject]:
    """모든 과목 조회"""
    result = await session.execute(select(Subject).order_by(Subject.id))
    return result.scalars().all()


async def get_all_subjects_with_quiz_count(session: AsyncSession) -> list[dict]:
    """모든 과목 조회 (문제 개수 포함)"""
    # LEFT JOIN으로 각 과목의 문제 개수 계산
    stmt = (
        select(
            Subject.id,
            Subject.name,
            Subject.description,
            Subject.created_at,
            func.count(Quiz.id).label("quiz_count")
        )
        .outerjoin(Quiz, Subject.id == Quiz.subject_id)
        .group_by(Subject.id, Subject.name, Subject.description, Subject.created_at)
        .order_by(Subject.id)
    )
    result = await session.execute(stmt)
    
    # 딕셔너리 리스트로 변환
    subjects = []
    for row in result.all():
        subjects.append({
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "created_at": row.created_at,
            "quiz_count": row.quiz_count or 0,
        })
    return subjects
