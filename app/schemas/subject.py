from datetime import datetime

from pydantic import BaseModel, Field


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
