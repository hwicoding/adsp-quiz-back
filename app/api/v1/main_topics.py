from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import main_topic as main_topic_crud
from app.models.base import get_db
from app.schemas import main_topic as main_topic_schema

router = APIRouter(prefix="/main-topics", tags=["main-topics"])

# ADsP 전용 구조: subject_id는 항상 1 (ADsP)
ADSP_SUBJECT_ID = 1


@router.get("", response_model=main_topic_schema.MainTopicListResponse)
async def get_all_main_topics(
    db: AsyncSession = Depends(get_db),
):
    """주요항목 목록 조회 API (ADsP 전용)"""
    main_topics = await main_topic_crud.get_all_main_topics(db)
    main_topic_responses = [
        main_topic_schema.MainTopicResponse.model_validate(mt) for mt in main_topics
    ]
    return main_topic_schema.MainTopicListResponse(
        main_topics=main_topic_responses,
        total=len(main_topic_responses)
    )


@router.get("/{main_topic_id}", response_model=main_topic_schema.MainTopicResponse)
async def get_main_topic(
    main_topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    """주요항목 상세 조회 API"""
    main_topic = await main_topic_crud.get_main_topic_by_id(db, main_topic_id)
    if not main_topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"주요항목을 찾을 수 없습니다: {main_topic_id}",
        )
    return main_topic_schema.MainTopicResponse.model_validate(main_topic)
