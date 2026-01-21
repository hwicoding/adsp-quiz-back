import asyncio
import json
import logging
import os
import random

from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

from app.core.config import settings
from app.exceptions import GeminiServiceUnavailableError, GeminiAPIKeyError
from app.schemas.ai import AIQuizGenerationRequest, AIQuizGenerationResponse

logger = logging.getLogger(__name__)

_gemini_client: genai.Client | None = None
# 동시 Gemini API 요청 수 제한 (과부하 방지)
_gemini_semaphore: asyncio.Semaphore | None = None


def get_gemini_client() -> genai.Client:
    """Gemini 클라이언트 싱글톤"""
    global _gemini_client
    if _gemini_client is None:
        api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def get_gemini_semaphore() -> asyncio.Semaphore:
    """Gemini API 동시 요청 제한 Semaphore 싱글톤"""
    global _gemini_semaphore
    if _gemini_semaphore is None:
        # 환경변수에서 동시 요청 수 가져오기 (기본값: 2)
        max_concurrent = int(os.getenv("GEMINI_MAX_CONCURRENT", "2"))
        _gemini_semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"Gemini API 동시 요청 제한 설정: 최대 {max_concurrent}개")
    return _gemini_semaphore


async def generate_quiz_with_gemini(request: AIQuizGenerationRequest) -> AIQuizGenerationResponse:
    """Gemini를 사용하여 문제 생성 (무료, 재시도 로직 포함, 동시 요청 제한)"""
    client = get_gemini_client()
    semaphore = get_gemini_semaphore()
    
    prompt = f"""당신은 교육용 문제 생성 전문가입니다.

{request.subject_name} 과목 객관식 문제 1개를 생성하세요.

텍스트: {request.source_text}

다음 JSON 형식으로 응답하세요:
{{
  "question": "문제 내용",
  "options": [
    {{"index": 0, "text": "정답 선택지"}},
    {{"index": 1, "text": "오답 선택지 1"}},
    {{"index": 2, "text": "오답 선택지 2"}},
    {{"index": 3, "text": "오답 선택지 3"}},
    {{"index": 4, "text": "오답 선택지 4"}},
    {{"index": 5, "text": "오답 선택지 5"}},
    {{"index": 6, "text": "오답 선택지 6"}}
  ],
  "correct_answer": 0,
  "explanation": "해설"
}}

요구사항:
- 명확한 문제
- 정답 1개 (index: 0)
- 오답 6개 (index: 1-6, 매력적인 오답으로 구성)
- 정답 인덱스는 항상 0
- 간결한 해설
- 오답들은 정답과 유사하지만 틀린 내용이어야 함"""

    # 재시도 설정 (503 에러 대응 강화)
    max_retries = 5  # 재시도 횟수 증가 (3회 → 5회)
    base_delay = 2.0  # 초기 대기 시간 증가 (1초 → 2초)
    max_delay = 16.0  # 최대 대기 시간 제한 (16초)
    
    # Semaphore로 동시 요청 수 제한 (과부하 방지)
    async with semaphore:
        logger.debug(f"Gemini API 요청 시작 (동시 요청 제한: 최대 {semaphore._value + 1}개)")
        
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
                
                # 성공 시 로그 출력 (첫 시도가 아니면)
                if attempt > 0:
                    logger.info(f"Gemini API 호출 성공 (시도 {attempt + 1}/{max_retries})")
                
                return AIQuizGenerationResponse(**data)
                
            except ClientError as e:
                # 403 에러 확인 (API 키 문제)
                error_message = str(e).lower()
                if "403" in str(e) or "permission_denied" in error_message or "leaked" in error_message:
                    logger.error(
                        f"Gemini API 키 문제 감지: status_code=403, "
                        f"error_type={type(e).__name__}"
                    )
                    raise GeminiAPIKeyError(
                        "Gemini API 키 문제로 문제 생성에 실패했습니다. 관리자에게 문의하세요."
                    )
                else:
                    # 403이 아닌 다른 ClientError는 그대로 전파
                    logger.error(
                        f"Gemini API ClientError: status_code={getattr(e, 'status_code', 'unknown')}, "
                        f"error_type={type(e).__name__}"
                    )
                    raise
            except ServerError as e:
                # 503 에러 확인
                error_message = str(e)
                if "503" in error_message or "UNAVAILABLE" in error_message or "overloaded" in error_message.lower():
                    if attempt < max_retries - 1:
                        # 지수 백오프 + jitter: 2초, 4초, 8초, 16초 (최대 16초)
                        exponential_delay = base_delay * (2 ** attempt)
                        delay = min(exponential_delay, max_delay)
                        # Jitter 추가: ±20% 랜덤 변동으로 동시 요청 분산
                        jitter = delay * 0.2 * (random.random() * 2 - 1)  # -20% ~ +20%
                        delay_with_jitter = max(0.5, delay + jitter)  # 최소 0.5초 보장
                        
                        logger.warning(
                            f"Gemini API 503 에러 발생 (시도 {attempt + 1}/{max_retries}). "
                            f"{delay_with_jitter:.1f}초 후 재시도합니다. (에러: {error_message[:100]})"
                        )
                        await asyncio.sleep(delay_with_jitter)
                        continue
                    else:
                        # 최대 재시도 횟수 도달
                        logger.error(
                            f"Gemini API 503 에러: 최대 재시도 횟수({max_retries}) 도달. "
                            f"총 {max_retries}회 시도 후 실패. 에러 메시지: {error_message}"
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
                logger.error(
                    f"Gemini API 호출 중 예외 발생: error_type={type(e).__name__}, "
                    f"error_message={str(e)[:200]}"
                )
                raise


async def generate_quiz(request: AIQuizGenerationRequest) -> AIQuizGenerationResponse:
    """AI를 사용하여 문제 생성 (Gemini 사용)"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다")
    return await generate_quiz_with_gemini(request)
