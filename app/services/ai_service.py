import asyncio
import json
import logging
import os

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from app.core.config import settings
from app.exceptions import GeminiServiceUnavailableError
from app.schemas.ai import AIQuizGenerationRequest, AIQuizGenerationResponse

logger = logging.getLogger(__name__)

_gemini_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:
    """Gemini 클라이언트 싱글톤"""
    global _gemini_client
    if _gemini_client is None:
        api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


async def generate_quiz_with_gemini(request: AIQuizGenerationRequest) -> AIQuizGenerationResponse:
    """Gemini를 사용하여 문제 생성 (무료, 재시도 로직 포함)"""
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

    # 재시도 설정
    max_retries = 3
    base_delay = 1.0  # 초기 대기 시간 (초)
    
    for attempt in range(max_retries):
        try:
            # Gemini는 동기 API이므로 asyncio로 래핑
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        response_mime_type="application/json",
                    ),
                )
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
            
        except ServerError as e:
            # 503 에러 확인
            error_message = str(e)
            if "503" in error_message or "UNAVAILABLE" in error_message or "overloaded" in error_message.lower():
                if attempt < max_retries - 1:
                    # 지수 백오프: 1초, 2초, 4초
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Gemini API 503 에러 발생 (시도 {attempt + 1}/{max_retries}). "
                        f"{delay:.1f}초 후 재시도합니다."
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # 최대 재시도 횟수 도달
                    logger.error(
                        f"Gemini API 503 에러: 최대 재시도 횟수({max_retries}) 도달. "
                        f"에러 메시지: {error_message}"
                    )
                    raise GeminiServiceUnavailableError(
                        "Gemini API가 일시적으로 과부하 상태입니다. 잠시 후 다시 시도해주세요."
                    )
            else:
                # 503이 아닌 다른 ServerError는 그대로 전파
                logger.error(f"Gemini API ServerError (503 아님): {error_message}")
                raise
        except Exception as e:
            # 다른 예외는 재시도하지 않고 즉시 전파
            logger.error(f"Gemini API 호출 중 예외 발생: {e.__class__.__name__}: {str(e)}")
            raise


async def generate_quiz(request: AIQuizGenerationRequest) -> AIQuizGenerationResponse:
    """AI를 사용하여 문제 생성 (Gemini 사용)"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다")
    return await generate_quiz_with_gemini(request)
