import json
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz import Quiz
from app.schemas.ai import AIQuizGenerationResponse


async def get_quiz_by_id(session: AsyncSession, quiz_id: int) -> Quiz | None:
    """ID로 문제 조회"""
    result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
    return result.scalar_one_or_none()


async def get_quiz_by_hash(session: AsyncSession, source_hash: str) -> Quiz | None:
    """해시로 중복 문제 확인"""
    result = await session.execute(select(Quiz).where(Quiz.source_hash == source_hash))
    return result.scalar_one_or_none()


async def create_quiz(
    session: AsyncSession,
    subject_id: int,
    ai_response: AIQuizGenerationResponse,
    source_hash: str,
    source_url: str | None = None,
    source_text: str | None = None,
    sub_topic_id: int | None = None,
) -> Quiz:
    """문제 생성"""
    quiz = Quiz(
        subject_id=subject_id,
        sub_topic_id=sub_topic_id,
        question=ai_response.question,
        options=ai_response.options_json,
        correct_answer=ai_response.correct_answer,
        explanation=ai_response.explanation,
        source_hash=source_hash,
        source_url=source_url,
        source_text=source_text,
    )
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)
    return quiz


async def get_random_quizzes(
    session: AsyncSession,
    subject_id: int,
    count: int,
) -> Sequence[Quiz]:
    """과목별 랜덤 문제 추출 (DB 레벨 최적화)"""
    from sqlalchemy import func
    
    # 전체 개수 확인
    count_stmt = select(func.count(Quiz.id)).where(Quiz.subject_id == subject_id)
    total_count = await session.scalar(count_stmt)
    
    if total_count is None or total_count == 0:
        return []
    
    # DB 레벨에서 랜덤 샘플링 (PostgreSQL의 ORDER BY RANDOM() 사용)
    stmt = (
        select(Quiz)
        .where(Quiz.subject_id == subject_id)
        .order_by(func.random())
        .limit(count)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_quizzes_by_sub_topic_id(
    session: AsyncSession,
    sub_topic_id: int,
    count: int,
    exclude_quiz_ids: list[int] | None = None,
) -> Sequence[Quiz]:
    """세부항목별 문제 조회 (캐시 조회용, 이미 본 문제 제외 가능)"""
    from sqlalchemy import func
    
    stmt = select(Quiz).where(Quiz.sub_topic_id == sub_topic_id)
    
    # 이미 본 문제 제외
    if exclude_quiz_ids:
        stmt = stmt.where(~Quiz.id.in_(exclude_quiz_ids))
    
    stmt = stmt.order_by(func.random()).limit(count)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_quiz_count_by_sub_topic_id(
    session: AsyncSession,
    sub_topic_id: int,
) -> int:
    """세부항목별 문제 개수 조회"""
    from sqlalchemy import func
    
    count_stmt = select(func.count(Quiz.id)).where(Quiz.sub_topic_id == sub_topic_id)
    total_count = await session.scalar(count_stmt)
    return total_count or 0
