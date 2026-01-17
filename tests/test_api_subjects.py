"""Subjects API 통합 테스트"""
import pytest

from app.models.quiz import Quiz
from app.models.subject import Subject


@pytest.mark.asyncio
async def test_get_subjects(client, test_db_session):
    """과목 목록 조회 (프론트엔드 요청 형식)"""
    subject1 = Subject(id=1, name="ADsP 데이터 분석 준전문가", description="데이터 분석 준전문가 자격증 시험")
    subject2 = Subject(id=2, name="SQLD", description="SQL 개발자 자격증 시험")
    test_db_session.add(subject1)
    test_db_session.add(subject2)
    
    # subject1에 문제 2개 추가
    quiz1 = Quiz(
        subject_id=1,
        question="문제1",
        options='[{"index": 0, "text": "선택지1"}]',
        correct_answer=0,
        source_hash="hash1",
    )
    quiz2 = Quiz(
        subject_id=1,
        question="문제2",
        options='[{"index": 0, "text": "선택지1"}]',
        correct_answer=0,
        source_hash="hash2",
    )
    test_db_session.add(quiz1)
    test_db_session.add(quiz2)
    await test_db_session.commit()
    
    response = client.get("/api/v1/subjects")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["name"] == "ADsP 데이터 분석 준전문가"
    assert data[0]["description"] == "데이터 분석 준전문가 자격증 시험"
    assert data[0]["quiz_count"] == 2
    assert data[1]["id"] == 2
    assert data[1]["name"] == "SQLD"
    assert data[1]["quiz_count"] == 0


@pytest.mark.asyncio
async def test_get_subjects_empty(client, test_db_session):
    """과목 목록 조회 (과목 없음)"""
    response = client.get("/api/v1/subjects")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
