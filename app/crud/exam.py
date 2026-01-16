from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_record import ExamRecord


async def create_exam_record(
    session: AsyncSession,
    quiz_id: int,
    exam_session_id: str,
    user_answer: int | None = None,
) -> ExamRecord:
    """시험 기록 생성"""
    from app.crud.quiz import get_quiz_by_id
    
    quiz = await get_quiz_by_id(session, quiz_id)
    if not quiz:
        raise ValueError(f"문제를 찾을 수 없습니다: {quiz_id}")
    
    is_correct = None
    if user_answer is not None:
        is_correct = user_answer == quiz.correct_answer
    
    record = ExamRecord(
        quiz_id=quiz_id,
        exam_session_id=exam_session_id,
        user_answer=user_answer,
        is_correct=is_correct,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_exam_records_by_session(
    session: AsyncSession,
    exam_session_id: str,
) -> Sequence[ExamRecord]:
    """시험 세션 ID로 기록 조회"""
    stmt = select(ExamRecord).where(ExamRecord.exam_session_id == exam_session_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_exam_record_by_session_and_quiz(
    session: AsyncSession,
    exam_session_id: str,
    quiz_id: int,
) -> ExamRecord | None:
    """시험 세션 ID와 문제 ID로 기록 조회"""
    stmt = select(ExamRecord).where(
        ExamRecord.exam_session_id == exam_session_id,
        ExamRecord.quiz_id == quiz_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_exam_record_answer(
    session: AsyncSession,
    record: ExamRecord,
    user_answer: int,
    is_correct: bool,
) -> ExamRecord:
    """시험 기록 답안 업데이트"""
    record.user_answer = user_answer
    record.is_correct = is_correct
    await session.commit()
    await session.refresh(record)
    return record
