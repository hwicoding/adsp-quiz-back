from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz_validation import QuizValidation


async def create_quiz_validation(
    session: AsyncSession,
    quiz_id: int,
    validation_status: str,
    validation_score: int | None = None,
    feedback: str | None = None,
    issues: list[str] | None = None,
) -> QuizValidation:
    """검증 결과 저장"""
    validation = QuizValidation(
        quiz_id=quiz_id,
        validation_status=validation_status,
        validation_score=validation_score,
        feedback=feedback,
        issues=issues,
    )
    session.add(validation)
    await session.commit()
    await session.refresh(validation)
    return validation


async def get_latest_validation(
    session: AsyncSession,
    quiz_id: int,
) -> QuizValidation | None:
    """문제의 최신 검증 결과 조회"""
    stmt = (
        select(QuizValidation)
        .where(QuizValidation.quiz_id == quiz_id)
        .order_by(desc(QuizValidation.validated_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_quizzes_needing_validation(
    session: AsyncSession,
) -> list[int]:
    """검증이 필요한 문제 ID 목록 조회 (pending 또는 invalid 상태, 또는 검증 이력이 없는 문제)"""
    from app.models.quiz import Quiz
    
    # 각 문제의 최신 검증 상태를 서브쿼리로 조회
    latest_validation_subquery = (
        select(
            QuizValidation.quiz_id,
            QuizValidation.validation_status,
            func.row_number()
            .over(
                partition_by=QuizValidation.quiz_id,
                order_by=desc(QuizValidation.validated_at)
            )
            .label('rn')
        )
        .subquery()
    )
    
    # 최신 검증 상태만 필터링
    latest_status = (
        select(
            latest_validation_subquery.c.quiz_id,
            latest_validation_subquery.c.validation_status
        )
        .where(latest_validation_subquery.c.rn == 1)
        .subquery()
    )
    
    # 검증이 필요한 문제: 최신 상태가 'pending' 또는 'invalid'이거나 검증 이력이 없는 문제
    stmt = (
        select(Quiz.id)
        .outerjoin(latest_status, Quiz.id == latest_status.c.quiz_id)
        .where(
            (latest_status.c.validation_status.in_(['pending', 'invalid']))
            | (latest_status.c.validation_status.is_(None))
        )
    )
    
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_validation_status_counts(
    session: AsyncSession,
) -> dict[str, int]:
    """검증 상태별 개수 조회"""
    from app.models.quiz import Quiz
    
    # 전체 문제 개수
    total_count = await session.scalar(select(func.count(Quiz.id))) or 0
    
    # 최신 검증 상태별 개수
    latest_status_subquery = (
        select(
            QuizValidation.quiz_id,
            QuizValidation.validation_status,
            func.row_number()
            .over(
                partition_by=QuizValidation.quiz_id,
                order_by=desc(QuizValidation.validated_at)
            )
            .label('rn')
        )
        .subquery()
    )
    
    # valid, invalid 개수
    valid_count_stmt = (
        select(func.count())
        .select_from(latest_status_subquery)
        .where(
            (latest_status_subquery.c.rn == 1)
            & (latest_status_subquery.c.validation_status == 'valid')
        )
    )
    valid_count = await session.scalar(valid_count_stmt) or 0
    
    invalid_count_stmt = (
        select(func.count())
        .select_from(latest_status_subquery)
        .where(
            (latest_status_subquery.c.rn == 1)
            & (latest_status_subquery.c.validation_status == 'invalid')
        )
    )
    invalid_count = await session.scalar(invalid_count_stmt) or 0
    
    # pending = 전체 - valid - invalid
    pending_count = total_count - valid_count - invalid_count
    
    return {
        "valid": valid_count,
        "invalid": invalid_count,
        "pending": pending_count,
    }
