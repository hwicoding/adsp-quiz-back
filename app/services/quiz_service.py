import logging
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import quiz as quiz_crud, subject as subject_crud, sub_topic as sub_topic_crud
from app.exceptions import (
    GeminiServiceUnavailableError,
    InvalidQuizRequestError,
    QuizNotFoundError,
    SubjectNotFoundError,
    SubTopicNotFoundError,
)
from app.schemas import ai, exam as exam_schema, quiz as quiz_schema
from app.services import ai_service, quiz_variation, youtube_service

logger = logging.getLogger(__name__)


async def generate_quiz(
    session: AsyncSession,
    request: quiz_schema.QuizCreateRequest,
) -> quiz_schema.QuizResponse:
    """단일 문제 생성"""
    # subject_id가 None이면 기본 과목(id=1, ADsP) 사용
    subject_id = request.subject_id or 1
    subject = await subject_crud.get_subject_by_id(session, subject_id)
    if not subject:
        raise SubjectNotFoundError(subject_id)

    source_text = None
    source_url = None

    if request.source_type == "url":
        if not request.source_url:
            raise InvalidQuizRequestError("source_type이 'url'일 때 source_url은 필수입니다")
        video_id = youtube_service.extract_video_id(request.source_url)
        source_text = await youtube_service.extract_transcript(video_id)
        source_url = request.source_url
    else:
        if not request.source_text:
            raise InvalidQuizRequestError("source_type이 'text'일 때 source_text는 필수입니다")
        source_text = request.source_text

    source_hash = youtube_service.generate_hash(source_text)

    existing_quiz = await quiz_crud.get_quiz_by_hash(session, source_hash)
    if existing_quiz:
        return quiz_schema.QuizResponse.model_validate(existing_quiz)

    ai_request = ai.AIQuizGenerationRequest(
        source_text=source_text,
        subject_name=subject.name,
    )
    
    try:
        ai_response = await ai_service.generate_quiz(ai_request)
    except GeminiServiceUnavailableError:
        raise

    new_quiz = await quiz_crud.create_quiz(
        session,
        subject_id=subject_id,
        ai_response=ai_response,
        source_hash=source_hash,
        source_url=source_url,
        source_text=request.source_text if request.source_type == "text" else None,
    )

    return quiz_schema.QuizResponse.model_validate(new_quiz)


async def generate_study_quizzes(
    session: AsyncSession,
    request: quiz_schema.StudyModeQuizCreateRequest,
) -> quiz_schema.StudyModeQuizListResponse:
    """학습 모드 문제 생성 (10개 일괄 생성, 캐싱 지원)"""
    # 세부항목 존재 확인
    sub_topic = await sub_topic_crud.get_sub_topic_with_core_content(session, request.sub_topic_id)
    if not sub_topic:
        raise SubTopicNotFoundError(request.sub_topic_id)
    
    # 핵심 정보 확인
    if not sub_topic.core_content:
        raise InvalidQuizRequestError(f"세부항목에 핵심 정보가 없습니다: {request.sub_topic_id}")
    
    # 캐시된 문제 조회
    cached_quizzes = await quiz_crud.get_quizzes_by_sub_topic_id(
        session,
        request.sub_topic_id,
        request.quiz_count
    )
    
    # 캐시된 문제가 충분한 경우
    if len(cached_quizzes) >= request.quiz_count:
        logger.info(
            f"캐시된 문제 사용: sub_topic_id={request.sub_topic_id}, "
            f"요청={request.quiz_count}, 캐시={len(cached_quizzes)}"
        )
        quiz_responses = [
            quiz_schema.QuizResponse.model_validate(q) for q in cached_quizzes[:request.quiz_count]
        ]
        return quiz_schema.StudyModeQuizListResponse(
            quizzes=quiz_responses,
            total_count=len(quiz_responses)
        )
    
    # 부족한 문제 개수 계산
    needed_count = request.quiz_count - len(cached_quizzes)
    logger.info(
        f"새 문제 생성 필요: sub_topic_id={request.sub_topic_id}, "
        f"요청={request.quiz_count}, 캐시={len(cached_quizzes)}, 생성={needed_count}"
    )
    
    # 새 문제 생성
    new_quizzes = []
    subject_id = sub_topic.main_topic.subject_id
    
    for i in range(needed_count):
        try:
            # 핵심 정보를 기반으로 문제 생성
            ai_request = ai.AIQuizGenerationRequest(
                source_text=sub_topic.core_content,
                subject_name=sub_topic.main_topic.subject.name,
            )
            
            ai_response = await ai_service.generate_quiz(ai_request)
            
            # 해시 생성 (핵심 정보 + 인덱스로 고유성 보장)
            source_hash = youtube_service.generate_hash(
                f"{sub_topic.core_content}_{request.sub_topic_id}_{i}"
            )
            
            # 중복 확인
            existing_quiz = await quiz_crud.get_quiz_by_hash(session, source_hash)
            if existing_quiz:
                # 이미 존재하는 문제는 캐시에 추가
                if existing_quiz.sub_topic_id != request.sub_topic_id:
                    # 다른 세부항목의 문제인 경우 sub_topic_id 업데이트
                    existing_quiz.sub_topic_id = request.sub_topic_id
                    await session.commit()
                    await session.refresh(existing_quiz)
                new_quizzes.append(existing_quiz)
                continue
            
            # 새 문제 생성
            new_quiz = await quiz_crud.create_quiz(
                session,
                subject_id=subject_id,
                ai_response=ai_response,
                source_hash=source_hash,
                source_url=None,
                source_text=sub_topic.core_content,
                sub_topic_id=request.sub_topic_id,
            )
            new_quizzes.append(new_quiz)
            
        except GeminiServiceUnavailableError as e:
            logger.error(
                f"Gemini API 과부하: sub_topic_id={request.sub_topic_id}, "
                f"생성 중단 (생성된 문제: {len(new_quizzes)}/{needed_count})"
            )
            # 일부 문제라도 생성되었으면 반환
            if new_quizzes or cached_quizzes:
                break
            # 문제가 하나도 없으면 에러 반환
            raise
        except Exception as e:
            logger.error(
                f"문제 생성 중 오류: sub_topic_id={request.sub_topic_id}, "
                f"에러={e.__class__.__name__}: {str(e)}",
                exc_info=True
            )
            # 일부 문제라도 생성되었으면 반환
            if new_quizzes or cached_quizzes:
                break
            raise
    
    # 캐시된 문제 + 새로 생성한 문제 합치기
    all_quizzes = list(cached_quizzes) + new_quizzes
    
    # 요청한 개수만큼만 반환
    quiz_responses = [
        quiz_schema.QuizResponse.model_validate(q) for q in all_quizzes[:request.quiz_count]
    ]
    
    logger.info(
        f"학습 모드 문제 생성 완료: sub_topic_id={request.sub_topic_id}, "
        f"요청={request.quiz_count}, 반환={len(quiz_responses)} "
        f"(캐시={len(cached_quizzes)}, 신규={len(new_quizzes)})"
    )
    
    return quiz_schema.StudyModeQuizListResponse(
        quizzes=quiz_responses,
        total_count=len(quiz_responses)
    )


async def get_next_study_quiz(
    session: AsyncSession,
    sub_topic_id: int,
    exclude_quiz_ids: list[int] | None = None,
) -> quiz_schema.QuizResponse:
    """학습 모드 다음 문제 요청 (점진적 생성, 1개씩, 이미 본 문제 제외)"""
    # 세부항목 존재 확인
    sub_topic = await sub_topic_crud.get_sub_topic_with_core_content(session, sub_topic_id)
    if not sub_topic:
        raise SubTopicNotFoundError(sub_topic_id)
    
    # 핵심 정보 확인
    if not sub_topic.core_content:
        raise InvalidQuizRequestError(f"세부항목에 핵심 정보가 없습니다: {sub_topic_id}")
    
    # 1. DB에서 해당 세부항목의 기존 문제 조회 (랜덤 1개, 이미 본 문제 제외)
    existing_quizzes = await quiz_crud.get_quizzes_by_sub_topic_id(
        session,
        sub_topic_id,
        1,  # 1개만 조회
        exclude_quiz_ids=exclude_quiz_ids,
    )
    
    # 2. 기존 문제가 있으면 변형하여 반환 (토큰 절약)
    if existing_quizzes:
        existing_quiz = existing_quizzes[0]
        quiz_response = quiz_schema.QuizResponse.model_validate(existing_quiz)
        
        # 문제 변형 (선택지 순서 섞기 또는 문제 문장 변형)
        # 70% 확률로 변형, 30% 확률로 원본 그대로
        if random.random() < 0.7:
            quiz_response = quiz_variation.vary_quiz(quiz_response)
            logger.info(
                f"기존 문제 변형하여 반환: quiz_id={existing_quiz.id}, "
                f"sub_topic_id={sub_topic_id} (토큰 0개 사용)"
            )
        else:
            logger.info(
                f"기존 문제 그대로 반환: quiz_id={existing_quiz.id}, "
                f"sub_topic_id={sub_topic_id} (토큰 0개 사용)"
            )
        
        return quiz_response
    
    # 2-1. 기존 문제가 없거나 모두 본 문제인 경우
    # DB에 문제가 충분한지 확인 (exclude_ids 제외하고)
    total_quiz_count = await quiz_crud.get_quiz_count_by_sub_topic_id(session, sub_topic_id)
    available_count = total_quiz_count - (len(exclude_quiz_ids) if exclude_quiz_ids else 0)
    
    # 사용 가능한 문제가 3개 미만이면 자동으로 새 문제 생성 (다양성 보장)
    if available_count < 3:
        logger.info(
            f"사용 가능한 문제 부족 ({available_count}개 < 3개). "
            f"새 문제 자동 생성: sub_topic_id={sub_topic_id} (토큰 1개 사용)"
        )
    else:
        # 사용 가능한 문제가 있는데 조회되지 않은 경우는 없어야 하지만, 혹시 모르니 새로 생성
        logger.warning(
            f"사용 가능한 문제가 있지만 조회되지 않음 ({available_count}개). "
            f"새 문제 생성: sub_topic_id={sub_topic_id} (토큰 1개 사용)"
        )
        existing_quiz = existing_quizzes[0]
        quiz_response = quiz_schema.QuizResponse.model_validate(existing_quiz)
        
        # 문제 변형 (선택지 순서 섞기 또는 문제 문장 변형)
        # 70% 확률로 변형, 30% 확률로 원본 그대로
        if random.random() < 0.7:
            quiz_response = quiz_variation.vary_quiz(quiz_response)
            logger.info(
                f"기존 문제 변형하여 반환: quiz_id={existing_quiz.id}, "
                f"sub_topic_id={sub_topic_id} (토큰 0개 사용)"
            )
        else:
            logger.info(
                f"기존 문제 그대로 반환: quiz_id={existing_quiz.id}, "
                f"sub_topic_id={sub_topic_id} (토큰 0개 사용)"
            )
        
        return quiz_response
    
    # 3. 기존 문제가 없으면 Gemini API로 새로 생성 (토큰 1개 사용)
    logger.info(
        f"새 문제 생성: sub_topic_id={sub_topic_id} (토큰 1개 사용)"
    )
    
    subject_id = sub_topic.main_topic.subject_id
    
    try:
        # 핵심 정보를 기반으로 문제 생성
        ai_request = ai.AIQuizGenerationRequest(
            source_text=sub_topic.core_content,
            subject_name=sub_topic.main_topic.subject.name,
        )
        
        ai_response = await ai_service.generate_quiz(ai_request)
        
        # 해시 생성 (핵심 정보 기반)
        source_hash = youtube_service.generate_hash(
            f"{sub_topic.core_content}_{sub_topic_id}_{random.randint(1000, 9999)}"
        )
        
        # 중복 확인
        existing_quiz = await quiz_crud.get_quiz_by_hash(session, source_hash)
        if existing_quiz:
            # 이미 존재하는 문제는 변형하여 반환
            quiz_response = quiz_schema.QuizResponse.model_validate(existing_quiz)
            quiz_response = quiz_variation.vary_quiz(quiz_response)
            logger.info(
                f"중복 문제 변형하여 반환: quiz_id={existing_quiz.id}, "
                f"sub_topic_id={sub_topic_id} (토큰 0개 사용)"
            )
            return quiz_response
        
        # 새 문제 생성
        new_quiz = await quiz_crud.create_quiz(
            session,
            subject_id=subject_id,
            ai_response=ai_response,
            source_hash=source_hash,
            source_url=None,
            source_text=sub_topic.core_content,
            sub_topic_id=sub_topic_id,
        )
        
        quiz_response = quiz_schema.QuizResponse.model_validate(new_quiz)
        logger.info(
            f"새 문제 생성 완료: quiz_id={new_quiz.id}, "
            f"sub_topic_id={sub_topic_id} (토큰 1개 사용)"
        )
        
        return quiz_response
        
    except GeminiServiceUnavailableError:
        logger.error(f"Gemini API 과부하: sub_topic_id={sub_topic_id}")
        raise
    except Exception as e:
        logger.error(
            f"문제 생성 중 오류: sub_topic_id={sub_topic_id}, "
            f"에러={e.__class__.__name__}: {str(e)}",
            exc_info=True
        )
        raise
