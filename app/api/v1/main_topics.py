from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import main_topic as main_topic_crud, subject as subject_crud
from app.models.base import get_db
from app.schemas import main_topic as main_topic_schema

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("/{subject_id}/main-topics", response_model=main_topic_schema.MainTopicListResponse)
async def get_main_topics(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
):
    """주요항목 목록 조회 API"""
    # 과목 존재 확인
    subject = await subject_crud.get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"과목을 찾을 수 없습니다: {subject_id}",
        )
    
    main_topics = await main_topic_crud.get_main_topics_by_subject_id(db, subject_id)
    main_topic_responses = [
        main_topic_schema.MainTopicResponse.model_validate(mt) for mt in main_topics
    ]
    return main_topic_schema.MainTopicListResponse(
        main_topics=main_topic_responses,
        total=len(main_topic_responses)
    )
