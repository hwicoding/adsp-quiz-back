from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import quiz as quiz_crud, subject as subject_crud
from app.exceptions import InvalidQuizRequestError, QuizNotFoundError
from app.models.base import get_db
from app.schemas import quiz as quiz_schema, subject as subject_schema
from app.services import quiz_service

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.get("/subjects", response_model=subject_schema.SubjectListResponse)
async def get_subjects(
    db: AsyncSession = Depends(get_db),
):
    """과목 목록 조회 API"""
    subjects = await subject_crud.get_all_subjects(db)
    subject_responses = [subject_schema.SubjectResponse.model_validate(s) for s in subjects]
    return subject_schema.SubjectListResponse(subjects=subject_responses, total=len(subject_responses))


@router.post("/generate", response_model=quiz_schema.QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    request: quiz_schema.QuizCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """문제 생성 API (프론트엔드 호환: camelCase 필드명 지원, subject_id 선택 필드)"""
    return await quiz_service.generate_quiz(db, request)


@router.get("/dashboard", response_model=quiz_schema.QuizDashboardResponse)
async def get_quiz_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """관리자 대시보드 API: 문제 목록과 카테고리 매칭 상태 시각화"""
    return await quiz_service.get_quiz_dashboard(db)


@router.get("/{quiz_id}", response_model=quiz_schema.QuizResponse)
async def get_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
):
    """문제 조회 API"""
    quiz = await quiz_crud.get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise QuizNotFoundError(quiz_id)

    return quiz_schema.QuizResponse.model_validate(quiz)


@router.post("/generate-study", response_model=quiz_schema.StudyModeQuizListResponse, status_code=status.HTTP_201_CREATED)
async def generate_study_quizzes(
    request: quiz_schema.StudyModeQuizCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """학습 모드 문제 생성 API (10개 일괄 생성, 캐싱 지원)"""
    return await quiz_service.generate_study_quizzes(db, request)


@router.get("/study/next", response_model=quiz_schema.QuizResponse)
async def get_next_study_quiz(
    sub_topic_id: int,
    exclude_quiz_ids: str | None = None,  # 콤마로 구분된 문제 ID 리스트 (예: "1,2,3")
    db: AsyncSession = Depends(get_db),
):
    """학습 모드 다음 문제 요청 API (점진적 생성, 1개씩, 이미 본 문제 제외)"""
    # 이미 본 문제 ID 파싱
    exclude_ids = None
    if exclude_quiz_ids:
        try:
            exclude_ids = [int(id_str.strip()) for id_str in exclude_quiz_ids.split(",") if id_str.strip()]
        except ValueError:
            raise InvalidQuizRequestError("exclude_quiz_ids는 콤마로 구분된 숫자 리스트여야 합니다 (예: '1,2,3')")
    
    return await quiz_service.get_next_study_quiz(db, sub_topic_id, exclude_ids)


@router.put("/{quiz_id}", response_model=quiz_schema.QuizResponse)
async def update_quiz(
    quiz_id: int,
    request: quiz_schema.QuizUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """문제 수정 API (카테고리 검증 후 수정 가능)"""
    import json
    
    quiz = await quiz_crud.get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise QuizNotFoundError(quiz_id)
    
    # options를 JSON 문자열로 변환
    options_json = None
    if request.options is not None:
        options_json = json.dumps(
            [{"index": opt.index, "text": opt.text} for opt in request.options],
            ensure_ascii=False
        )
    
    updated_quiz = await quiz_crud.update_quiz(
        db,
        quiz_id,
        question=request.question,
        options=options_json,
        correct_answer=request.correct_answer,
        explanation=request.explanation,
        sub_topic_id=request.sub_topic_id,
    )
    
    if not updated_quiz:
        raise QuizNotFoundError(quiz_id)
    
    return quiz_schema.QuizResponse.model_validate(updated_quiz)


@router.post("/{quiz_id}/validate", response_model=quiz_schema.QuizValidationResponse)
async def validate_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
):
    """문제 검증 API: Gemini로 생성된 문제가 카테고리에 맞는지 재검증"""
    return await quiz_service.validate_quiz(db, quiz_id)


@router.post("/{quiz_id}/correction", response_model=quiz_schema.QuizCorrectionResponse)
async def request_quiz_correction(
    quiz_id: int,
    request: quiz_schema.QuizCorrectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """문제 수정 요청 API: 사용자 피드백을 Gemini로 검증 후 수정"""
    # URL의 quiz_id를 사용 (request의 quiz_id는 무시)
    request.quiz_id = quiz_id
    return await quiz_service.request_quiz_correction(db, request)
