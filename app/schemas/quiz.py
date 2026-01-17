import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QuizCreateRequest(BaseModel):
    """문제 생성 요청 스키마"""
    source_type: Literal["url", "text"] = Field(..., description="입력 소스 타입")
    source_url: str | None = Field(None, description="YouTube URL (source_type='url'일 때 필수)")
    source_text: str | None = Field(None, description="텍스트 입력 (source_type='text'일 때 필수)")
    subject_id: int = Field(..., description="과목 ID")

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: str | None, info) -> str | None:
        if info.data.get("source_type") == "url" and not v:
            raise ValueError("source_type이 'url'일 때 source_url은 필수입니다")
        return v

    @field_validator("source_text")
    @classmethod
    def validate_text(cls, v: str | None, info) -> str | None:
        if info.data.get("source_type") == "text" and not v:
            raise ValueError("source_type이 'text'일 때 source_text는 필수입니다")
        return v


class ExamStartRequest(BaseModel):
    """시험 시작 요청 스키마"""
    subject_id: int = Field(..., description="과목 ID")
    quiz_count: int = Field(..., ge=1, le=50, description="문제 개수 (1-50)")


class ExamSubmitRequest(BaseModel):
    """답안 제출 요청 스키마"""
    exam_session_id: str = Field(..., description="시험 세션 ID")
    quiz_id: int = Field(..., description="문제 ID")
    user_answer: int = Field(..., ge=0, le=3, description="사용자 답안 (0-3)")


class QuizOptionResponse(BaseModel):
    """문제 선택지 응답 스키마"""
    index: int = Field(..., description="선택지 인덱스 (0-3)")
    text: str = Field(..., description="선택지 텍스트")


class QuizResponse(BaseModel):
    """문제 응답 스키마"""
    id: int
    subject_id: int
    question: str
    options: list[QuizOptionResponse]
    correct_answer: int | None = Field(None, description="정답 (시험 중에는 None)")
    explanation: str | None
    source_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_options(cls, data: dict) -> dict:
        """DB의 JSON 문자열 options를 리스트로 변환"""
        if isinstance(data, dict) and "options" in data:
            options_str = data.get("options")
            if isinstance(options_str, str):
                try:
                    options_list = json.loads(options_str)
                    data["options"] = [
                        QuizOptionResponse(**opt) if isinstance(opt, dict) else opt
                        for opt in options_list
                    ]
                except (json.JSONDecodeError, TypeError):
                    data["options"] = []
        return data


class QuizListResponse(BaseModel):
    """문제 목록 응답 스키마"""
    quizzes: list[QuizResponse]
    total: int


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


class SubjectResponse(BaseModel):
    """과목 응답 스키마"""
    id: int
    name: str
    description: str | None
    quiz_count: int | None = Field(None, description="해당 과목의 문제 개수 (선택사항)")
    created_at: datetime

    model_config = {"from_attributes": True}


class SubjectListResponse(BaseModel):
    """과목 목록 응답 스키마"""
    subjects: list[SubjectResponse]
    total: int
