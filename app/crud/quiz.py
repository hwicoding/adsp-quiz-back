import json
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.quiz import Quiz
from app.models.sub_topic import SubTopic
from app.models.main_topic import MainTopic
from app.schemas.ai import AIQuizGenerationResponse


async def get_quiz_by_id(
    session: AsyncSession, 
    quiz_id: int,
    load_relationships: bool = False,
) -> Quiz | None:
    """ID로 문제 조회
    
    Args:
        session: 데이터베이스 세션
        quiz_id: 문제 ID
        load_relationships: 관계(sub_topic, subject)를 eager load할지 여부
    """
    stmt = select(Quiz).where(Quiz.id == quiz_id)
    
    if load_relationships:
        stmt = stmt.options(
            joinedload(Quiz.sub_topic).joinedload(SubTopic.main_topic).joinedload(MainTopic.subject),
            joinedload(Quiz.subject),
        )
    
    result = await session.execute(stmt)
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


def _calculate_question_similarity(q1: str, q2: str) -> float:
    """문제 텍스트 유사도 계산 (토큰 없이, Jaccard 유사도 사용)
    
    Args:
        q1: 첫 번째 문제 텍스트
        q2: 두 번째 문제 텍스트
    
    Returns:
        0.0 ~ 1.0 사이의 유사도 (1.0이 완전 동일)
    """
    # 공백 제거 및 소문자 변환 (한글은 변환 불필요)
    words1 = set(q1.replace("?", "").replace(".", "").split())
    words2 = set(q2.replace("?", "").replace(".", "").split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard 유사도: 교집합 / 합집합
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union) if union else 0.0


async def get_similar_quizzes_by_question(
    session: AsyncSession,
    sub_topic_id: int,
    question: str,
    similarity_threshold: float = 0.7,
    limit: int = 10,
) -> Sequence[Quiz]:
    """세부항목별 유사 문제 조회 (토큰 없이)
    
    Args:
        session: 데이터베이스 세션
        sub_topic_id: 세부항목 ID
        question: 비교할 문제 텍스트
        similarity_threshold: 유사도 임계값 (기본값: 0.7)
        limit: 최대 조회 개수
    
    Returns:
        유사도가 임계값 이상인 문제 목록
    """
    # 세부항목의 모든 문제 조회
    stmt = select(Quiz).where(Quiz.sub_topic_id == sub_topic_id)
    result = await session.execute(stmt)
    all_quizzes = result.scalars().all()
    
    # 유사도 계산하여 필터링
    similar_quizzes = []
    for quiz in all_quizzes:
        similarity = _calculate_question_similarity(question, quiz.question)
        if similarity >= similarity_threshold:
            similar_quizzes.append(quiz)
            if len(similar_quizzes) >= limit:
                break
    
    return similar_quizzes


async def update_quiz(
    session: AsyncSession,
    quiz_id: int,
    question: str | None = None,
    options: str | None = None,
    correct_answer: int | None = None,
    explanation: str | None = None,
    sub_topic_id: int | None = None,
) -> Quiz | None:
    """문제 수정"""
    quiz = await get_quiz_by_id(session, quiz_id)
    if not quiz:
        return None
    
    if question is not None:
        quiz.question = question
    if options is not None:
        quiz.options = options
    if correct_answer is not None:
        quiz.correct_answer = correct_answer
    if explanation is not None:
        quiz.explanation = explanation
    if sub_topic_id is not None:
        quiz.sub_topic_id = sub_topic_id
    
    await session.commit()
    await session.refresh(quiz)
    return quiz
