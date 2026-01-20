"""Main Topics API 통합 테스트"""
import pytest

from app.models.subject import Subject
from app.models.main_topic import MainTopic


@pytest.mark.asyncio
async def test_get_all_main_topics(client, test_db_session):
    """주요항목 목록 조회 (ADsP 전용)"""
    subject = Subject(id=1, name="ADsP", description="테스트 과목")
    main_topic1 = MainTopic(id=1, subject_id=1, name="주요항목1", description="테스트 주요항목1")
    main_topic2 = MainTopic(id=2, subject_id=1, name="주요항목2", description="테스트 주요항목2")
    test_db_session.add(subject)
    test_db_session.add(main_topic1)
    test_db_session.add(main_topic2)
    await test_db_session.commit()
    
    response = client.get("/api/v1/main-topics")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["main_topics"]) == 2
    assert data["main_topics"][0]["id"] == 1
    assert data["main_topics"][0]["name"] == "주요항목1"
    assert data["main_topics"][1]["id"] == 2
    assert data["main_topics"][1]["name"] == "주요항목2"


@pytest.mark.asyncio
async def test_get_main_topic(client, test_db_session):
    """주요항목 상세 조회"""
    subject = Subject(id=1, name="ADsP", description="테스트 과목")
    main_topic = MainTopic(id=1, subject_id=1, name="주요항목1", description="테스트 주요항목")
    test_db_session.add(subject)
    test_db_session.add(main_topic)
    await test_db_session.commit()
    
    response = client.get("/api/v1/main-topics/1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "주요항목1"
    assert data["subject_id"] == 1


@pytest.mark.asyncio
async def test_get_main_topic_not_found(client, test_db_session):
    """주요항목 상세 조회 (존재하지 않는 ID)"""
    response = client.get("/api/v1/main-topics/999")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "주요항목을 찾을 수 없습니다" in data["detail"]
