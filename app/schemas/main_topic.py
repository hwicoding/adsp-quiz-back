from datetime import datetime

from pydantic import BaseModel, Field


class MainTopicResponse(BaseModel):
    """주요항목 응답 스키마"""
    id: int
    name: str
    description: str | None
    subject_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MainTopicListResponse(BaseModel):
    """주요항목 목록 응답 스키마"""
    main_topics: list[MainTopicResponse]
    total: int
