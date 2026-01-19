import json

import google.generativeai as genai

from app.core.config import settings
from app.schemas.ai import AIQuizGenerationRequest, AIQuizGenerationResponse

_gemini_client: genai.GenerativeModel | None = None


def get_gemini_client() -> genai.GenerativeModel:
    """Gemini 클라이언트 싱글톤"""
    global _gemini_client
    if _gemini_client is None:
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_client = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            generation_config={
                "temperature": 0.7,
                "response_mime_type": "application/json",
            },
        )
    return _gemini_client


async def generate_quiz_with_gemini(request: AIQuizGenerationRequest) -> AIQuizGenerationResponse:
    """Gemini를 사용하여 문제 생성 (무료)"""
    import asyncio
    
    client = get_gemini_client()
    
    prompt = f"""당신은 교육용 문제 생성 전문가입니다.

{request.subject_name} 과목 객관식 문제 1개를 생성하세요.

텍스트: {request.source_text}

다음 JSON 형식으로 응답하세요:
{{
  "question": "문제 내용",
  "options": [
    {{"index": 0, "text": "선택지 1"}},
    {{"index": 1, "text": "선택지 2"}},
    {{"index": 2, "text": "선택지 3"}},
    {{"index": 3, "text": "선택지 4"}}
  ],
  "correct_answer": 0,
  "explanation": "해설"
}}

요구사항:
- 명확한 문제
- 선택지 4개 (index: 0-3)
- 정답 인덱스 (0-3)
- 간결한 해설"""

    # Gemini는 동기 API이므로 asyncio로 래핑
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.generate_content(prompt)
    )
    
    result = response.text
    if not result:
        raise ValueError("AI 응답이 비어있습니다")
    
    # JSON 파싱 (마크다운 코드 블록 제거)
    result = result.strip()
    if result.startswith("```json"):
        result = result[7:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()
    
    data = json.loads(result)
    return AIQuizGenerationResponse(**data)


async def generate_quiz(request: AIQuizGenerationRequest) -> AIQuizGenerationResponse:
    """AI를 사용하여 문제 생성 (Gemini 사용)"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다")
    return await generate_quiz_with_gemini(request)
