from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import quiz as quiz_crud
from app.models.base import get_db
from app.schemas import ai, quiz as quiz_schema
from app.services import ai_service, youtube_service

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.get("/subjects", response_model=quiz_schema.SubjectListResponse)
async def get_subjects(
    db: AsyncSession = Depends(get_db),
):
    """과목 목록 조회 API"""
    subjects = await quiz_crud.get_all_subjects(db)
    subject_responses = [quiz_schema.SubjectResponse.model_validate(s) for s in subjects]
    return quiz_schema.SubjectListResponse(subjects=subject_responses, total=len(subject_responses))


@router.post("/generate", response_model=quiz_schema.QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    request: quiz_schema.QuizCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """문제 생성 API"""
    subject = await quiz_crud.get_subject_by_id(db, request.subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"과목을 찾을 수 없습니다: {request.subject_id}",
        )

    source_text = None
    source_url = None

    if request.source_type == "url":
        if not request.source_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_type이 'url'일 때 source_url은 필수입니다",
            )
        video_id = youtube_service.extract_video_id(request.source_url)
        source_text = await youtube_service.extract_transcript(video_id)
        source_url = request.source_url
    else:
        if not request.source_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_type이 'text'일 때 source_text는 필수입니다",
            )
        source_text = request.source_text

    source_hash = youtube_service.generate_hash(source_text)

    existing_quiz = await quiz_crud.get_quiz_by_hash(db, source_hash)
    if existing_quiz:
        return quiz_schema.QuizResponse.model_validate(existing_quiz)

    ai_request = ai.AIQuizGenerationRequest(
        source_text=source_text,
        subject_name=subject.name,
    )
    ai_response = await ai_service.generate_quiz(ai_request)

    new_quiz = await quiz_crud.create_quiz(
        db,
        subject_id=request.subject_id,
        ai_response=ai_response,
        source_hash=source_hash,
        source_url=source_url,
        source_text=request.source_text if request.source_type == "text" else None,
    )

    return quiz_schema.QuizResponse.model_validate(new_quiz)


@router.get("/{quiz_id}", response_model=quiz_schema.QuizResponse)
async def get_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
):
    """문제 조회 API"""
    quiz = await quiz_crud.get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문제를 찾을 수 없습니다: {quiz_id}",
        )

    return quiz_schema.QuizResponse.model_validate(quiz)
