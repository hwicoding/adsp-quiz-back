import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QuizCreateRequest(BaseModel):
    """문제 생성 요청 스키마 (프론트엔드 호환: camelCase 필드명 지원)"""
    # 프론트엔드 호환: source (camelCase) 또는 source_type (snake_case) 모두 허용
    source: Literal["youtube", "text"] | None = Field(None, description="입력 소스 타입 (프론트엔드: 'youtube' | 'text')")
    source_type: Literal["url", "text", "youtube"] | None = Field(None, description="입력 소스 타입 (백엔드: 'url' | 'text')")
    
    # 프론트엔드 호환: content (camelCase) 또는 source_url/source_text (snake_case) 모두 허용
    content: str | None = Field(None, description="입력 내용 (프론트엔드: YouTube URL 또는 텍스트)")
    source_url: str | None = Field(None, description="YouTube URL (source_type='url' 또는 'youtube'일 때 필수)")
    source_text: str | None = Field(None, description="텍스트 입력 (source_type='text'일 때 필수)")
    
    # 과목 선택 안 함 지원: subject_id를 선택 필드로 변경
    subject_id: int | None = Field(None, description="과목 ID (None일 때 기본 과목 사용)")

    model_config = {"populate_by_name": True}  # alias와 원래 필드명 모두 허용

    @model_validator(mode="before")
    @classmethod
    def normalize_request(cls, data: dict) -> dict:
        """프론트엔드 요청 형식을 백엔드 형식으로 변환"""
        if isinstance(data, dict):
            # source (프론트엔드) → source_type (백엔드) 변환
            if "source" in data and "source_type" not in data:
                source_value = data["source"]
                if source_value == "youtube":
                    data["source_type"] = "url"
                elif source_value == "text":
                    data["source_type"] = "text"
            
            # content (프론트엔드) → source_url 또는 source_text (백엔드) 변환
            if "content" in data:
                content_value = data["content"]
                source_type = data.get("source_type") or data.get("source")
                
                if source_type in ("url", "youtube"):
                    if "source_url" not in data:
                        data["source_url"] = content_value
                elif source_type == "text":
                    if "source_text" not in data:
                        data["source_text"] = content_value
        return data

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str | None, info) -> str:
        """source_type 검증 및 정규화"""
        # source 필드에서 변환 시도
        if v is None:
            source_value = info.data.get("source")
            if source_value == "youtube":
                return "url"
            elif source_value == "text":
                return "text"
            raise ValueError("source 또는 source_type 필드가 필요합니다")
        
        # "youtube"를 "url"로 변환
        if v == "youtube":
            return "url"
        return v

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: str | None, info) -> str | None:
        source_type = info.data.get("source_type") or info.data.get("source")
        if source_type in ("url", "youtube") and not v:
            # content 필드에서 가져오기 시도
            content = info.data.get("content")
            if content:
                return content
            raise ValueError("source_type이 'url' 또는 'youtube'일 때 source_url 또는 content는 필수입니다")
        return v

    @field_validator("source_text")
    @classmethod
    def validate_text(cls, v: str | None, info) -> str | None:
        source_type = info.data.get("source_type") or info.data.get("source")
        if source_type == "text" and not v:
            # content 필드에서 가져오기 시도
            content = info.data.get("content")
            if content:
                return content
            raise ValueError("source_type이 'text'일 때 source_text 또는 content는 필수입니다")
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
