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
    """세부항목 핵심 정보 조회 API (관리 페이지용)
    
    관리 페이지에서 등록/수정을 위해 사용되므로, 세부항목이 없어도 빈 값으로 반환합니다.
    core_content가 null이면 빈 문자열로 처리하여 등록 폼을 표시할 수 있도록 합니다.
    """
    logger.info(f"세부항목 핵심 정보 조회 시작: sub_topic_id={sub_topic_id}")
    
    try:
        sub_topic = await sub_topic_crud.get_sub_topic_with_core_content(db, sub_topic_id)
    except Exception as e:
        logger.error(
            f"세부항목 조회 중 DB 에러: sub_topic_id={sub_topic_id}, "
            f"error={e.__class__.__name__}: {str(e)}",
            exc_info=True
        )
        raise
    
    if not sub_topic:
        logger.warning(f"세부항목을 찾을 수 없음: sub_topic_id={sub_topic_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세부항목을 찾을 수 없습니다: {sub_topic_id}",
        )
    
    logger.info(f"세부항목 핵심 정보 조회 완료: sub_topic_id={sub_topic_id}, name={sub_topic.name}, core_content={'있음' if sub_topic.core_content else '없음'}")
    
    # 관리 페이지용: core_content가 None이어도 정상 응답 (빈 값으로 처리)
    return sub_topic_schema.SubTopicCoreContentResponse.model_validate(sub_topic)
