"""Exam Service 테스트"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    ExamSessionNotFoundError,
    InvalidQuizRequestError,
    QuizNotFoundError,
    SubjectNotFoundError,
)
from app.schemas import exam as exam_schema
from app.services import exam_service


@pytest.fixture
def mock_db_session():
    """모킹된 DB 세션"""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_subject():
    """모킹된 과목"""
    subject = MagicMock()
    subject.id = 1
    subject.name = "데이터 분석"
    return subject


@pytest.fixture
def mock_quiz():
    """모킹된 문제"""
    quiz = MagicMock()
    quiz.id = 1
    quiz.subject_id = 1
    quiz.correct_answer = 0
    return quiz


@pytest.fixture
def mock_exam_record():
    """모킹된 시험 기록"""
    record = MagicMock()
    record.id = 1
    record.quiz_id = 1
    record.user_answer = None
    record.is_correct = None
    record.created_at = MagicMock()
    return record


@pytest.mark.asyncio
async def test_start_exam_subject_not_found(mock_db_session):
    """과목을 찾을 수 없을 때 예외 발생"""
    from app.crud import subject as subject_crud
    
    with patch.object(subject_crud, "get_subject_by_id", return_value=None):
        request = exam_schema.ExamStartRequest(
            subject_id=999,  # ADsP가 아닌 경우 에러 발생
            quiz_count=10,
        )
        
        with pytest.raises(SubjectNotFoundError):
            await exam_service.start_exam(mock_db_session, request)


@pytest.mark.asyncio
async def test_start_exam_insufficient_quizzes(mock_db_session, mock_subject):
    """문제 개수가 부족할 때 예외 발생"""
    from app.crud import subject as subject_crud, quiz as quiz_crud
    
    with patch.object(subject_crud, "get_subject_by_id", return_value=mock_subject):
        with patch.object(quiz_crud, "get_random_quizzes", return_value=[]):
            request = exam_schema.ExamStartRequest(
                subject_id=1,
                quiz_count=10,
            )
            
            with pytest.raises(InvalidQuizRequestError):
                await exam_service.start_exam(mock_db_session, request)


@pytest.mark.asyncio
async def test_submit_answer_quiz_not_found(mock_db_session):
    """문제를 찾을 수 없을 때 예외 발생"""
    from app.crud import quiz as quiz_crud
    
    with patch.object(quiz_crud, "get_quiz_by_id", return_value=None):
        request = exam_schema.ExamSubmitRequest(
            exam_session_id="test-session",
            quiz_id=999,
            user_answer=0,
        )
        
        with pytest.raises(QuizNotFoundError):
            await exam_service.submit_answer(mock_db_session, request)


@pytest.mark.asyncio
async def test_submit_answer_exam_session_not_found(mock_db_session, mock_quiz):
    """시험 기록을 찾을 수 없을 때 예외 발생"""
    from app.crud import quiz as quiz_crud, exam as exam_crud
    
    with patch.object(quiz_crud, "get_quiz_by_id", return_value=mock_quiz):
        with patch.object(exam_crud, "get_exam_record_by_session_and_quiz", return_value=None):
            request = exam_schema.ExamSubmitRequest(
                exam_session_id="test-session",
                quiz_id=1,
                user_answer=0,
            )
            
            with pytest.raises(ExamSessionNotFoundError):
                await exam_service.submit_answer(mock_db_session, request)


@pytest.mark.asyncio
async def test_submit_answer_already_submitted(mock_db_session, mock_quiz, mock_exam_record):
    """이미 답안이 제출되었을 때 예외 발생"""
    from app.crud import quiz as quiz_crud, exam as exam_crud
    
    mock_exam_record.user_answer = 1  # 이미 제출됨
    
    with patch.object(quiz_crud, "get_quiz_by_id", return_value=mock_quiz):
        with patch.object(exam_crud, "get_exam_record_by_session_and_quiz", return_value=mock_exam_record):
            request = exam_schema.ExamSubmitRequest(
                exam_session_id="test-session",
                quiz_id=1,
                user_answer=0,
            )
            
            with pytest.raises(InvalidQuizRequestError):
                await exam_service.submit_answer(mock_db_session, request)


@pytest.mark.asyncio
async def test_get_exam_result_not_found(mock_db_session):
    """시험 기록을 찾을 수 없을 때 예외 발생"""
    from app.crud import exam as exam_crud
    
    with patch.object(exam_crud, "get_exam_records_by_session", return_value=[]):
        with pytest.raises(ExamSessionNotFoundError):
            await exam_service.get_exam_result(mock_db_session, "test-session")


@pytest.mark.asyncio
async def test_get_exam_result_quiz_not_found(mock_db_session, mock_exam_record):
    """시험 기록의 문제를 찾을 수 없을 때 예외 발생"""
    from app.crud import exam as exam_crud, quiz as quiz_crud
    
    with patch.object(exam_crud, "get_exam_records_by_session", return_value=[mock_exam_record]):
        with patch.object(quiz_crud, "get_quiz_by_id", return_value=None):
            with pytest.raises(QuizNotFoundError):
                await exam_service.get_exam_result(mock_db_session, "test-session")
