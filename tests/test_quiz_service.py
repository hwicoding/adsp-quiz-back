"""Quiz Service 테스트"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    InvalidQuizRequestError,
    SubjectNotFoundError,
    SubTopicNotFoundError,
)
from app.schemas import quiz as quiz_schema
from app.services import quiz_service


@pytest.fixture
def mock_db_session():
    """모킹된 DB 세션"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_subject():
    """모킹된 과목"""
    subject = MagicMock()
    subject.id = 1
    subject.name = "데이터 분석"
    return subject


@pytest.fixture
def mock_sub_topic():
    """모킹된 세부항목"""
    sub_topic = MagicMock()
    sub_topic.id = 1
    sub_topic.core_content = "테스트 핵심 정보"
    sub_topic.main_topic = MagicMock()
    sub_topic.main_topic.subject_id = 1
    sub_topic.main_topic.subject = MagicMock()
    sub_topic.main_topic.subject.name = "데이터 분석"
    return sub_topic


@pytest.mark.asyncio
async def test_generate_quiz_subject_not_found(mock_db_session, mock_subject):
    """과목을 찾을 수 없을 때 예외 발생"""
    from app.crud import subject as subject_crud
    
    with patch.object(subject_crud, "get_subject_by_id", return_value=None):
        request = quiz_schema.QuizCreateRequest(
            source_type="text",
            source_text="테스트 텍스트",
            subject_id=999,
        )
        
        with pytest.raises(SubjectNotFoundError):
            await quiz_service.generate_quiz(mock_db_session, request)


@pytest.mark.asyncio
async def test_generate_quiz_invalid_request_url(mock_db_session, mock_subject):
    """URL 타입인데 source_url이 없을 때 예외 발생"""
    from app.crud import subject as subject_crud
    
    with patch.object(subject_crud, "get_subject_by_id", return_value=mock_subject):
        request = quiz_schema.QuizCreateRequest(
            source_type="url",
            source_url=None,
            subject_id=1,
        )
        
        with pytest.raises(InvalidQuizRequestError):
            await quiz_service.generate_quiz(mock_db_session, request)


@pytest.mark.asyncio
async def test_generate_quiz_invalid_request_text(mock_db_session, mock_subject):
    """텍스트 타입인데 source_text가 없을 때 예외 발생"""
    from app.crud import subject as subject_crud
    
    with patch.object(subject_crud, "get_subject_by_id", return_value=mock_subject):
        request = quiz_schema.QuizCreateRequest(
            source_type="text",
            source_text=None,
            subject_id=1,
        )
        
        with pytest.raises(InvalidQuizRequestError):
            await quiz_service.generate_quiz(mock_db_session, request)


@pytest.mark.asyncio
async def test_generate_study_quizzes_sub_topic_not_found(mock_db_session):
    """세부항목을 찾을 수 없을 때 예외 발생"""
    from app.crud import sub_topic as sub_topic_crud
    
    with patch.object(sub_topic_crud, "get_sub_topic_with_core_content", return_value=None):
        request = quiz_schema.StudyModeQuizCreateRequest(
            sub_topic_id=999,
            quiz_count=10,
        )
        
        with pytest.raises(SubTopicNotFoundError):
            await quiz_service.generate_study_quizzes(mock_db_session, request)


@pytest.mark.asyncio
async def test_generate_study_quizzes_no_core_content(mock_db_session, mock_sub_topic):
    """핵심 정보가 없을 때 예외 발생"""
    from app.crud import sub_topic as sub_topic_crud
    
    mock_sub_topic.core_content = None
    
    with patch.object(sub_topic_crud, "get_sub_topic_with_core_content", return_value=mock_sub_topic):
        request = quiz_schema.StudyModeQuizCreateRequest(
            sub_topic_id=1,
            quiz_count=10,
        )
        
        with pytest.raises(InvalidQuizRequestError):
            await quiz_service.generate_study_quizzes(mock_db_session, request)


@pytest.mark.asyncio
async def test_get_next_study_quiz_sub_topic_not_found(mock_db_session):
    """세부항목을 찾을 수 없을 때 예외 발생"""
    from app.crud import sub_topic as sub_topic_crud
    
    with patch.object(sub_topic_crud, "get_sub_topic_with_core_content", return_value=None):
        with pytest.raises(SubTopicNotFoundError):
            await quiz_service.get_next_study_quiz(mock_db_session, 999, None)


@pytest.mark.asyncio
async def test_get_next_study_quiz_no_core_content(mock_db_session, mock_sub_topic):
    """핵심 정보가 없을 때 예외 발생"""
    from app.crud import sub_topic as sub_topic_crud
    
    mock_sub_topic.core_content = None
    
    with patch.object(sub_topic_crud, "get_sub_topic_with_core_content", return_value=mock_sub_topic):
        with pytest.raises(InvalidQuizRequestError):
            await quiz_service.get_next_study_quiz(mock_db_session, 1, None)
