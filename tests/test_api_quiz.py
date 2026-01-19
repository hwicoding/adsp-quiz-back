"""Quiz API 통합 테스트"""
import pytest
from unittest.mock import AsyncMock, patch

from app.models.quiz import Quiz
from app.models.subject import Subject


@pytest.mark.asyncio
async def test_generate_quiz_url(client, test_db_session):
    """URL로 문제 생성"""
    subject = Subject(id=1, name="데이터 분석")
    test_db_session.add(subject)
    await test_db_session.commit()
    
    with patch("app.services.youtube_service.extract_video_id", return_value="test_video_id"):
        with patch("app.services.youtube_service.extract_transcript", new_callable=AsyncMock, return_value="테스트 자막"):
            with patch("app.services.youtube_service.generate_hash", return_value="test_hash"):
                with patch("app.services.ai_service.generate_quiz", new_callable=AsyncMock) as mock_ai:
                    from app.schemas.ai import AIQuizGenerationResponse, AIQuizOption
                    mock_ai.return_value = AIQuizGenerationResponse(
                        question="테스트 문제",
                        options=[
                            AIQuizOption(index=0, text="선택지1"),
                            AIQuizOption(index=1, text="선택지2"),
                            AIQuizOption(index=2, text="선택지3"),
                            AIQuizOption(index=3, text="선택지4"),
                        ],
                        correct_answer=0,
                        explanation="설명",
                    )
                    
                    response = client.post(
                        "/api/v1/quiz/generate",
                        json={
                            "subject_id": 1,
                            "source_type": "url",
                            "source_url": "https://youtube.com/watch?v=test",
                        },
                    )
                    
                    assert response.status_code == 201
                    data = response.json()
                    assert "id" in data
                    assert data["question"] == "테스트 문제"


@pytest.mark.asyncio
async def test_generate_quiz_text(client, test_db_session):
    """텍스트로 문제 생성"""
    subject = Subject(id=1, name="데이터 분석")
    test_db_session.add(subject)
    await test_db_session.commit()
    
    with patch("app.services.youtube_service.generate_hash", return_value="test_hash"):
        with patch("app.services.ai_service.generate_quiz", new_callable=AsyncMock) as mock_ai:
                from app.schemas.ai import AIQuizGenerationResponse, AIQuizOption
                mock_ai.return_value = AIQuizGenerationResponse(
                    question="테스트 문제",
                    options=[
                        AIQuizOption(index=0, text="선택지1"),
                        AIQuizOption(index=1, text="선택지2"),
                        AIQuizOption(index=2, text="선택지3"),
                        AIQuizOption(index=3, text="선택지4"),
                    ],
                    correct_answer=0,
                    explanation="설명",
                )
                
                response = client.post(
                    "/api/v1/quiz/generate",
                    json={
                        "subject_id": 1,
                        "source_type": "text",
                        "source_text": "테스트 텍스트",
                    },
                )
                
                assert response.status_code == 201


@pytest.mark.asyncio
async def test_generate_quiz_duplicate(client, test_db_session):
    """중복 문제 생성 시 기존 문제 반환"""
    subject = Subject(id=1, name="데이터 분석")
    test_db_session.add(subject)
    await test_db_session.commit()
    
    quiz = Quiz(
        subject_id=1,
        question="기존 문제",
        options='[{"index": 0, "text": "선택지1"}]',
        correct_answer=0,
        source_hash="test_hash",
    )
    test_db_session.add(quiz)
    await test_db_session.commit()
    
    with patch("app.services.youtube_service.generate_hash", return_value="test_hash"):
        response = client.post(
                "/api/v1/quiz/generate",
                json={
                    "subject_id": 1,
                    "source_type": "text",
                    "source_text": "테스트 텍스트",
                },
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["question"] == "기존 문제"


@pytest.mark.asyncio
async def test_get_quiz(client, test_db_session):
    """문제 조회"""
    subject = Subject(id=1, name="데이터 분석")
    test_db_session.add(subject)
    await test_db_session.commit()
    
    quiz = Quiz(
        subject_id=1,
        question="테스트 문제",
        options='[{"index": 0, "text": "선택지1"}]',
        correct_answer=0,
        source_hash="test_hash",
    )
    test_db_session.add(quiz)
    await test_db_session.commit()
    
    response = client.get(f"/api/v1/quiz/{quiz.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == quiz.id
    assert data["question"] == "테스트 문제"


@pytest.mark.asyncio
async def test_get_quiz_not_found(client, test_db_session):
    """존재하지 않는 문제 조회"""
    response = client.get("/api/v1/quiz/999")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_subjects(client, test_db_session):
    """과목 목록 조회"""
    subject1 = Subject(id=1, name="ADsP", description="데이터 분석 준전문가")
    subject2 = Subject(id=2, name="SQLD", description="SQL 개발자")
    test_db_session.add(subject1)
    test_db_session.add(subject2)
    await test_db_session.commit()
    
    response = client.get("/api/v1/quiz/subjects")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["subjects"]) == 2
    assert data["subjects"][0]["id"] == 1
    assert data["subjects"][0]["name"] == "ADsP"
    assert data["subjects"][1]["id"] == 2
    assert data["subjects"][1]["name"] == "SQLD"


@pytest.mark.asyncio
async def test_get_subjects_empty(client, test_db_session):
    """과목 목록 조회 (과목 없음)"""
    response = client.get("/api/v1/quiz/subjects")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["subjects"]) == 0


@pytest.mark.asyncio
async def test_generate_quiz_frontend_format(client, test_db_session):
    """프론트엔드 형식(camelCase)으로 문제 생성"""
    subject = Subject(id=1, name="ADsP", description="데이터 분석 준전문가")
    test_db_session.add(subject)
    await test_db_session.commit()
    
    with patch("app.services.youtube_service.extract_video_id", return_value="test_video_id"):
        with patch("app.services.youtube_service.extract_transcript", new_callable=AsyncMock, return_value="테스트 자막"):
            with patch("app.services.youtube_service.generate_hash", return_value="test_hash"):
                with patch("app.services.ai_service.generate_quiz", new_callable=AsyncMock) as mock_ai:
                    from app.schemas.ai import AIQuizGenerationResponse, AIQuizOption
                    mock_ai.return_value = AIQuizGenerationResponse(
                        question="테스트 문제",
                        options=[
                            AIQuizOption(index=0, text="선택지1"),
                            AIQuizOption(index=1, text="선택지2"),
                            AIQuizOption(index=2, text="선택지3"),
                            AIQuizOption(index=3, text="선택지4"),
                        ],
                        correct_answer=0,
                        explanation="설명",
                    )
                    
                    # 프론트엔드 형식: source (camelCase), content (camelCase)
                    response = client.post(
                        "/api/v1/quiz/generate",
                        json={
                            "source": "youtube",
                            "content": "https://youtube.com/watch?v=test",
                        },
                    )
                    
                    assert response.status_code == 201
                    data = response.json()
                    assert "id" in data
                    assert data["question"] == "테스트 문제"


@pytest.mark.asyncio
async def test_generate_quiz_without_subject_id(client, test_db_session):
    """subject_id 없이 문제 생성 (기본 과목 사용)"""
    subject = Subject(id=1, name="ADsP", description="데이터 분석 준전문가")
    test_db_session.add(subject)
    await test_db_session.commit()
    
    with patch("app.services.youtube_service.generate_hash", return_value="test_hash"):
        with patch("app.services.ai_service.generate_quiz", new_callable=AsyncMock) as mock_ai:
            from app.schemas.ai import AIQuizGenerationResponse, AIQuizOption
            mock_ai.return_value = AIQuizGenerationResponse(
                question="테스트 문제",
                options=[
                    AIQuizOption(index=0, text="선택지1"),
                    AIQuizOption(index=1, text="선택지2"),
                    AIQuizOption(index=2, text="선택지3"),
                    AIQuizOption(index=3, text="선택지4"),
                ],
                correct_answer=0,
                explanation="설명",
            )
            
            # subject_id 없이 요청 (기본 과목 id=1 사용)
            response = client.post(
                "/api/v1/quiz/generate",
                json={
                    "source": "text",
                    "content": "테스트 텍스트",
                },
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["subject_id"] == 1  # 기본 과목 사용