import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import main_topic as main_topic_crud, sub_topic as sub_topic_crud
from app.models.base import get_db
from app.schemas import sub_topic as sub_topic_schema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/main-topics", tags=["main-topics"])


@router.get("/{main_topic_id}/sub-topics", response_model=sub_topic_schema.SubTopicListResponse)
async def get_sub_topics(
    main_topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    """세부항목 목록 조회 API"""
    # 주요항목 존재 확인
    main_topic = await main_topic_crud.get_main_topic_by_id(db, main_topic_id)
    if not main_topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"주요항목을 찾을 수 없습니다: {main_topic_id}",
        )
    
    sub_topics = await sub_topic_crud.get_sub_topics_by_main_topic_id(db, main_topic_id)
    sub_topic_responses = [
        sub_topic_schema.SubTopicResponse.model_validate(st) for st in sub_topics
    ]
    return sub_topic_schema.SubTopicListResponse(
        sub_topics=sub_topic_responses,
        total=len(sub_topic_responses)
    )


@router.put("/{main_topic_id}/sub-topics/{sub_topic_id}/core-content", response_model=sub_topic_schema.SubTopicCoreContentResponse)
async def update_sub_topic_core_content(
    main_topic_id: int,
    sub_topic_id: int,
    request: sub_topic_schema.SubTopicCoreContentUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """세부항목 핵심 정보 업데이트 API (관리자용)"""
    # 주요항목 존재 확인
    main_topic = await main_topic_crud.get_main_topic_by_id(db, main_topic_id)
    if not main_topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"주요항목을 찾을 수 없습니다: {main_topic_id}",
        )
    
    # 세부항목 존재 확인
    sub_topic = await sub_topic_crud.get_sub_topic_by_id(db, sub_topic_id)
    if not sub_topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세부항목을 찾을 수 없습니다: {sub_topic_id}",
        )
    
    # 세부항목이 해당 주요항목에 속하는지 확인
    if sub_topic.main_topic_id != main_topic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"세부항목({sub_topic_id})이 주요항목({main_topic_id})에 속하지 않습니다",
        )
    
    # 핵심 정보 업데이트
    updated_sub_topic = await sub_topic_crud.update_sub_topic_core_content(
        db,
        sub_topic_id,
        request.core_content,
    )
    
    if not updated_sub_topic:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="핵심 정보 업데이트 중 오류가 발생했습니다",
        )
    
    logger.info(f"세부항목 핵심 정보 업데이트: sub_topic_id={sub_topic_id}")
    
    return sub_topic_schema.SubTopicCoreContentResponse.model_validate(updated_sub_topic)
