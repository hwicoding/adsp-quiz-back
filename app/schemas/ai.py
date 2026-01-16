from pydantic import BaseModel, Field


class AIQuizOption(BaseModel):
    """AI 생성 문제 선택지 스키마"""
    index: int = Field(..., ge=0, le=3, description="선택지 인덱스 (0-3)")
    text: str = Field(..., description="선택지 텍스트")


class AIQuizGenerationRequest(BaseModel):
    """AI 문제 생성 요청 스키마 (내부 사용)"""
    source_text: str = Field(..., description="문제 생성 소스 텍스트")
    subject_name: str = Field(..., description="과목명")


class AIQuizGenerationResponse(BaseModel):
    """AI 문제 생성 응답 스키마 (Structured Output)"""
    question: str = Field(..., description="문제 내용")
    options: list[AIQuizOption] = Field(..., min_length=4, max_length=4, description="선택지 (4개 필수)")
    correct_answer: int = Field(..., ge=0, le=3, description="정답 인덱스 (0-3)")
    explanation: str = Field(..., description="해설")

    @property
    def options_json(self) -> str:
        """선택지를 JSON 문자열로 변환 (DB 저장용)"""
        import json
        return json.dumps([{"index": opt.index, "text": opt.text} for opt in self.options], ensure_ascii=False)
