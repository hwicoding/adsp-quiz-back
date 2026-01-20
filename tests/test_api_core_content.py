"""Core Content API 통합 테스트"""
import pytest

from app.models.subject import Subject
from app.models.main_topic import MainTopic
from app.models.sub_topic import SubTopic


@pytest.mark.asyncio
async def test_get_core_content(client, test_db_session):
    """세부항목 핵심 정보 조회"""
    subject = Subject(id=1, name="ADsP", description="테스트 과목")
    main_topic = MainTopic(id=1, subject_id=1, name="주요항목1", description="테스트 주요항목")
    sub_topic = SubTopic(
        id=1,
        main_topic_id=1,
        name="세부항목1",
        description="테스트 세부항목",
        core_content="핵심 정보 내용"
    )
    test_db_session.add(subject)
    test_db_session.add(main_topic)
    test_db_session.add(sub_topic)
    await test_db_session.commit()
    
    response = client.get("/api/v1/core-content/1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "세부항목1"
    assert data["core_content"] == "핵심 정보 내용"
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_core_content_not_found(client, test_db_session):
    """세부항목 핵심 정보 조회 (존재하지 않는 ID)"""
    response = client.get("/api/v1/core-content/999")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "세부항목을 찾을 수 없습니다" in data["detail"]


@pytest.mark.asyncio
async def test_get_core_content_null(client, test_db_session):
    """세부항목 핵심 정보 조회 (core_content가 null인 경우)"""
    subject = Subject(id=1, name="ADsP", description="테스트 과목")
    main_topic = MainTopic(id=1, subject_id=1, name="주요항목1", description="테스트 주요항목")
    sub_topic = SubTopic(
        id=1,
        main_topic_id=1,
        name="세부항목1",
        description="테스트 세부항목",
        core_content=None
    )
    test_db_session.add(subject)
    test_db_session.add(main_topic)
    test_db_session.add(sub_topic)
    await test_db_session.commit()
    
    response = client.get("/api/v1/core-content/1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "세부항목1"
    assert data["core_content"] is None
