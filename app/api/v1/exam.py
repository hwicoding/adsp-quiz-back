from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.schemas import exam as exam_schema, quiz as quiz_schema
from app.services import exam_service

router = APIRouter(prefix="/exam", tags=["exam"])


@router.post("/start", response_model=quiz_schema.QuizListResponse)
async def start_exam(
    request: exam_schema.ExamStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """시험 시작 API"""
    return await exam_service.start_exam(db, request)


@router.post("/submit", response_model=exam_schema.ExamRecordResponse)
async def submit_answer(
    request: exam_schema.ExamSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """답안 제출 API"""
    return await exam_service.submit_answer(db, request)


@router.get("/{exam_session_id}", response_model=exam_schema.ExamResponse)
async def get_exam_result(
    exam_session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """시험 결과 조회 API"""
    return await exam_service.get_exam_result(db, exam_session_id)
