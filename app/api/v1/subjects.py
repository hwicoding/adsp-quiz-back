import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import quiz as quiz_crud
from app.models.base import get_db
from app.schemas import quiz as quiz_schema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[quiz_schema.SubjectResponse])
async def get_subjects(
    db: AsyncSession = Depends(get_db),
):
    """과목 목록 조회 API (프론트엔드 요청 형식)"""
    try:
        subjects_data = await quiz_crud.get_all_subjects_with_quiz_count(db)
        return [quiz_schema.SubjectResponse.model_validate(subject) for subject in subjects_data]
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
