import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import sub_topic as sub_topic_crud
from app.models.base import get_db
from app.schemas import sub_topic as sub_topic_schema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/core-content", tags=["core-content"])


@router.get("/{sub_topic_id}", response_model=sub_topic_schema.SubTopicCoreContentResponse)
async def get_core_content(
    sub_topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    """세부항목 핵심 정보 조회 API"""
    sub_topic = await sub_topic_crud.get_sub_topic_with_core_content(db, sub_topic_id)
    if not sub_topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세부항목을 찾을 수 없습니다: {sub_topic_id}",
        )
    
    logger.info(f"세부항목 핵심 정보 조회: sub_topic_id={sub_topic_id}")
    
    return sub_topic_schema.SubTopicCoreContentResponse.model_validate(sub_topic)
