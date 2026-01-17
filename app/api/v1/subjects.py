from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import quiz as quiz_crud
from app.models.base import get_db
from app.schemas import quiz as quiz_schema

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[quiz_schema.SubjectResponse])
async def get_subjects(
    db: AsyncSession = Depends(get_db),
):
    """과목 목록 조회 API (프론트엔드 요청 형식)"""
    subjects_data = await quiz_crud.get_all_subjects_with_quiz_count(db)
    return [quiz_schema.SubjectResponse(**subject) for subject in subjects_data]
