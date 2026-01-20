from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.quiz import QuizResponse  # 순환 참조 방지를 위해 여기서 import


class ExamStartRequest(BaseModel):
    """시험 시작 요청 스키마 (ADsP 전용, subject_id는 선택 필드)"""
    subject_id: int | None = Field(None, description="과목 ID (None일 때 ADsP 사용)")
    quiz_count: int = Field(..., ge=1, le=50, description="문제 개수 (1-50)")


class ExamSubmitRequest(BaseModel):
    """답안 제출 요청 스키마"""
    exam_session_id: str = Field(..., description="시험 세션 ID")
    quiz_id: int = Field(..., description="문제 ID")
    user_answer: int = Field(..., ge=0, le=3, description="사용자 답안 (0-3)")


class ExamRecordResponse(BaseModel):
    """시험 기록 응답 스키마"""
    id: int
    quiz_id: int
    user_answer: int | None
    is_correct: bool | None
    quiz: QuizResponse
    created_at: datetime

    model_config = {"from_attributes": True}


class ExamResponse(BaseModel):
    """시험 결과 응답 스키마"""
    exam_session_id: str
    subject_id: int
    total_questions: int
    correct_count: int
    incorrect_count: int
    records: list[ExamRecordResponse]
    created_at: datetime
