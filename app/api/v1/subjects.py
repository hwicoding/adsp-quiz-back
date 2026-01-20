import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import subject as subject_crud
from app.models.base import get_db
from app.schemas import subject as subject_schema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[subject_schema.SubjectResponse])
async def get_subjects(
    db: AsyncSession = Depends(get_db),
):
    """과목 목록 조회 API (ADsP 전용, 하위 호환성 유지)"""
    try:
        subjects_data = await subject_crud.get_all_subjects_with_quiz_count(db)
        return [subject_schema.SubjectResponse.model_validate(subject) for subject in subjects_data]
    except Exception as e:
        logger.error(
            f"과목 목록 조회 실패: {e.__class__.__name__}",
            exc_info=True,
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="과목 목록 조회 중 오류가 발생했습니다.",
        )
