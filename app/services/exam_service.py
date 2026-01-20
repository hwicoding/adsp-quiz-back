import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import exam as exam_crud, quiz as quiz_crud, subject as subject_crud
from app.exceptions import (
    BaseAppError,
    ExamSessionNotFoundError,
    InvalidQuizRequestError,
    QuizNotFoundError,
    SubjectNotFoundError,
)
from app.schemas import exam as exam_schema, quiz as quiz_schema

logger = logging.getLogger(__name__)


async def start_exam(
    session: AsyncSession,
    request: exam_schema.ExamStartRequest,
) -> quiz_schema.QuizListResponse:
    """시험 시작 (ADsP 전용)"""
    # ADsP 전용 구조: subject_id는 항상 1
    subject_id = request.subject_id or 1
    if subject_id != 1:
        raise SubjectNotFoundError(subject_id)
    
    try:
        subject = await subject_crud.get_subject_by_id(session, subject_id)
        if not subject:
            raise SubjectNotFoundError(subject_id)

        quizzes = await quiz_crud.get_random_quizzes(session, subject_id, request.quiz_count)
        
        if len(quizzes) < request.quiz_count:
            logger.warning(
                f"문제 개수 부족: 요청={request.quiz_count}, 실제={len(quizzes)}, "
                f"subject_id={subject_id}"
            )
            raise InvalidQuizRequestError(
                f"요청한 문제 개수({request.quiz_count})보다 적은 문제가 있습니다. 현재: {len(quizzes)}개"
            )

        exam_session_id = str(uuid.uuid4())

        # 배치로 시험 기록 생성 (트랜잭션 일관성 보장)
        try:
            records = []
            for quiz in quizzes:
                record = await exam_crud.create_exam_record(
                    session,
                    quiz_id=quiz.id,
                    exam_session_id=exam_session_id,
                )
                records.append(record)
            # 모든 기록 생성 후 일괄 커밋
            await session.commit()
            # commit 후 각 record를 refresh하여 id 등 생성된 값 반영
            for record in records:
                await session.refresh(record)
        except ValueError as e:
            logger.error(f"시험 기록 생성 실패: {e}, exam_session_id={exam_session_id}")
            await session.rollback()
            raise InvalidQuizRequestError(f"시험 기록 생성 중 오류가 발생했습니다: {str(e)}")
        except Exception as e:
            logger.error(f"시험 기록 생성 중 예상치 못한 오류: {e}, exam_session_id={exam_session_id}", exc_info=True)
            await session.rollback()
            raise

        quiz_responses = [quiz_schema.QuizResponse.model_validate(q) for q in quizzes]
        for qr in quiz_responses:
            qr.correct_answer = None

        logger.info(f"시험 시작 성공: exam_session_id={exam_session_id}, quiz_count={len(quizzes)}")
        return quiz_schema.QuizListResponse(quizzes=quiz_responses, total=len(quiz_responses))
    
    except BaseAppError:
        raise
    except Exception as e:
        logger.error(f"시험 시작 API 오류: {e}", exc_info=True)
        await session.rollback()
        raise


async def submit_answer(
    session: AsyncSession,
    request: exam_schema.ExamSubmitRequest,
) -> exam_schema.ExamRecordResponse:
    """답안 제출"""
    quiz = await quiz_crud.get_quiz_by_id(session, request.quiz_id)
    if not quiz:
        raise QuizNotFoundError(request.quiz_id)

    record = await exam_crud.get_exam_record_by_session_and_quiz(
        session,
        request.exam_session_id,
        request.quiz_id,
    )

    if not record:
        raise ExamSessionNotFoundError(request.exam_session_id)

    if record.user_answer is not None:
        raise InvalidQuizRequestError("이미 답안이 제출되었습니다")

    record = await exam_crud.update_exam_record_answer(
        session,
        record,
        request.user_answer,
        request.user_answer == quiz.correct_answer,
    )

    return exam_schema.ExamRecordResponse.model_validate(record)


async def get_exam_result(
    session: AsyncSession,
    exam_session_id: str,
) -> exam_schema.ExamResponse:
    """시험 결과 조회"""
    records = await exam_crud.get_exam_records_by_session(session, exam_session_id)
    
    if not records:
        raise ExamSessionNotFoundError(exam_session_id)

    correct_count = sum(1 for r in records if r.is_correct is True)
    incorrect_count = sum(1 for r in records if r.is_correct is False)
    
    record_responses = [exam_schema.ExamRecordResponse.model_validate(r) for r in records]
    
    first_record = records[0]
    quiz = await quiz_crud.get_quiz_by_id(session, first_record.quiz_id)
    if not quiz:
        raise QuizNotFoundError(first_record.quiz_id)

    # ADsP 전용 구조: subject_id는 항상 1
    return exam_schema.ExamResponse(
        exam_session_id=exam_session_id,
        subject_id=1,
        total_questions=len(records),
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        records=record_responses,
        created_at=first_record.created_at,
    )
