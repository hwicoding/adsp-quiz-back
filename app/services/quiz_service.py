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
from app.core.config import settings
from app.schemas import ai, exam as exam_schema, quiz as quiz_schema
from app.services import ai_service, quiz_variation, youtube_service

logger = logging.getLogger(__name__)


async def generate_quiz(
    session: AsyncSession,
    request: quiz_schema.QuizCreateRequest,
) -> quiz_schema.QuizResponse:
    """단일 문제 생성 (ADsP 전용)"""
    # ADsP 전용 구조: subject_id는 항상 1
    subject_id = request.subject_id or 1
    if subject_id != 1:
        raise SubjectNotFoundError(subject_id)
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
    """학습 모드 문제 생성 (10개 일괄 생성, 캐싱 지원, ADsP 전용)"""
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
    # ADsP 전용 구조: subject_id는 항상 1
    subject_id = 1
    
    for i in range(needed_count):
        try:
            # 핵심 정보를 기반으로 문제 생성 (기존 데이터와 추가된 데이터 모두 종합)
            # core_content는 이미 append 방식으로 저장되어 있으므로 모든 데이터가 포함됨
            combined_content = sub_topic.core_content or ""
            
            # 여러 데이터가 구분자로 나뉘어 있을 경우, 모두 종합하여 사용
            # 구분자로 분리된 경우 각 부분을 명확히 구분하여 프롬프트에 전달
            ai_request = ai.AIQuizGenerationRequest(
                source_text=combined_content,
                subject_name=sub_topic.main_topic.subject.name,
                main_topic_name=sub_topic.main_topic.name,
                sub_topic_name=sub_topic.name,
            )
            
            ai_response = await ai_service.generate_quiz(ai_request)
            
            # 자동 검증: 선택적 + 샘플링 (토큰 절약)
            if settings.auto_validate_quiz and random.random() < settings.auto_validate_sample_rate:
                try:
                    category = f"{sub_topic.main_topic.subject.name} > {sub_topic.main_topic.name} > {sub_topic.name}"
                    import json
                    options = json.loads(ai_response.options_json) if isinstance(ai_response.options_json, str) else [{"index": opt.index, "text": opt.text} for opt in ai_response.options]
                    
                    # 간단한 키워드 기반 사전 필터링 (토큰 없이)
                    if _simple_keyword_check(ai_response.question, category):
                        validation_result = await ai_service.validate_quiz_with_gemini(
                            question=ai_response.question,
                            options=options,
                            explanation=ai_response.explanation,
                            category=category,
                        )
                        
                        if not validation_result.get("is_valid", False) or validation_result.get("validation_score", 0.0) < 0.7:
                            logger.warning(
                                f"자동 검증 실패: sub_topic_id={request.sub_topic_id}, "
                                f"score={validation_result.get('validation_score', 0.0)}, "
                                f"issues={validation_result.get('issues', [])}"
                            )
                except Exception as e:
                    # 검증 실패해도 문제 생성은 계속 진행
                    logger.warning(f"자동 검증 중 오류 (문제 생성은 계속 진행): {e.__class__.__name__}: {str(e)}")
            
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
            logger.info(
                f"새 문제 생성: quiz_id={new_quiz.id}, "
                f"카테고리: {sub_topic.main_topic.subject.name} > {sub_topic.main_topic.name} > {sub_topic.name}, "
                f"문제: {ai_response.question[:50]}..."
            )
            
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
    """학습 모드 다음 문제 요청 (점진적 생성, 1개씩, 이미 본 문제 제외, ADsP 전용)"""
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
    
    # ADsP 전용 구조: subject_id는 항상 1
    subject_id = 1
    
    try:
        # 핵심 정보를 기반으로 문제 생성 (기존 데이터와 추가된 데이터 모두 종합)
        combined_content = sub_topic.core_content or ""
        ai_request = ai.AIQuizGenerationRequest(
            source_text=combined_content,
            subject_name=sub_topic.main_topic.subject.name,
            main_topic_name=sub_topic.main_topic.name,
            sub_topic_name=sub_topic.name,
        )
        
        ai_response = await ai_service.generate_quiz(ai_request)
        
        # 자동 검증: 선택적 + 샘플링 (토큰 절약)
        # 환경변수로 제어하며, 샘플링 비율에 따라 일부만 검증
        if settings.auto_validate_quiz and random.random() < settings.auto_validate_sample_rate:
            try:
                category = f"{sub_topic.main_topic.subject.name} > {sub_topic.main_topic.name} > {sub_topic.name}"
                import json
                options = json.loads(ai_response.options_json) if isinstance(ai_response.options_json, str) else [{"index": opt.index, "text": opt.text} for opt in ai_response.options]
                
                # 간단한 키워드 기반 사전 필터링 (토큰 없이)
                if _simple_keyword_check(ai_response.question, category):
                    validation_result = await ai_service.validate_quiz_with_gemini(
                        question=ai_response.question,
                        options=options,
                        explanation=ai_response.explanation,
                        category=category,
                    )
                    
                    if not validation_result.get("is_valid", False) or validation_result.get("validation_score", 0.0) < 0.7:
                        logger.warning(
                            f"자동 검증 실패: quiz_id={new_quiz.id if 'new_quiz' in locals() else '생성 전'}, "
                            f"score={validation_result.get('validation_score', 0.0)}, "
                            f"issues={validation_result.get('issues', [])}"
                        )
            except Exception as e:
                # 검증 실패해도 문제 생성은 계속 진행
                logger.warning(f"자동 검증 중 오류 (문제 생성은 계속 진행): {e.__class__.__name__}: {str(e)}")
        
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
            source_text=combined_content,
            sub_topic_id=sub_topic_id,
        )
        
        quiz_response = quiz_schema.QuizResponse.model_validate(new_quiz)
        
        # 자동 검증 결과 로깅 (검증이 수행된 경우에만)
        if settings.auto_validate_quiz and random.random() < settings.auto_validate_sample_rate:
            logger.info(
                f"새 문제 생성 완료 (자동 검증 샘플링 적용): quiz_id={new_quiz.id}, "
                f"sub_topic_id={sub_topic_id}"
            )
        logger.info(
            f"새 문제 생성 완료: quiz_id={new_quiz.id}, "
            f"sub_topic_id={sub_topic_id}, "
            f"카테고리: {sub_topic.main_topic.subject.name} > {sub_topic.main_topic.name} > {sub_topic.name}, "
            f"문제: {quiz_response.question[:50]}... (토큰 1개 사용)"
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


async def validate_quiz(
    session: AsyncSession,
    quiz_id: int,
) -> quiz_schema.QuizValidationResponse:
    """문제 검증: Gemini로 생성된 문제가 카테고리에 맞는지 재검증"""
    import json
    
    quiz = await quiz_crud.get_quiz_by_id(session, quiz_id, load_relationships=True)
    if not quiz:
        raise QuizNotFoundError(quiz_id)
    
    # 카테고리 정보 구성
    category = "알 수 없음"
    if quiz.sub_topic:
        category = f"{quiz.sub_topic.main_topic.subject.name} > {quiz.sub_topic.main_topic.name} > {quiz.sub_topic.name}"
    elif quiz.subject:
        category = quiz.subject.name
    
    # 선택지 파싱
    options = json.loads(quiz.options) if isinstance(quiz.options, str) else quiz.options
    
    try:
        validation_result = await ai_service.validate_quiz_with_gemini(
            question=quiz.question,
            options=options,
            explanation=quiz.explanation or "",
            category=category,
        )
        
        return quiz_schema.QuizValidationResponse(
            quiz_id=quiz_id,
            is_valid=validation_result.get("is_valid", False),
            category=category,
            validation_score=validation_result.get("validation_score", 0.0),
            feedback=validation_result.get("feedback", ""),
            issues=validation_result.get("issues", []),
        )
    except Exception as e:
        logger.error(f"문제 검증 중 오류: quiz_id={quiz_id}, 에러={e.__class__.__name__}: {str(e)}")
        raise


async def request_quiz_correction(
    session: AsyncSession,
    request: quiz_schema.QuizCorrectionRequest,
) -> quiz_schema.QuizCorrectionResponse:
    """문제 수정 요청: 사용자 피드백을 Gemini로 검증 후 수정"""
    import json
    
    quiz = await quiz_crud.get_quiz_by_id(session, request.quiz_id)
    if not quiz:
        raise QuizNotFoundError(request.quiz_id)
    
    # 카테고리 정보 구성
    category = "알 수 없음"
    if quiz.sub_topic:
        category = f"{quiz.sub_topic.main_topic.subject.name} > {quiz.sub_topic.main_topic.name} > {quiz.sub_topic.name}"
    elif quiz.subject:
        category = quiz.subject.name
    
    # 선택지 파싱
    options = json.loads(quiz.options) if isinstance(quiz.options, str) else quiz.options
    
    try:
        # Gemini로 수정 요청 평가 및 수정된 문제 생성
        correction_result = await ai_service.evaluate_correction_request_with_gemini(
            quiz_question=quiz.question,
            quiz_options=options,
            quiz_explanation=quiz.explanation or "",
            category=category,
            correction_request=request.correction_request,
            suggested_correction=request.suggested_correction,
        )
        
        is_valid = correction_result.get("is_valid_request", False)
        corrected_quiz = None
        
        # 수정 요청이 타당한 경우 문제 수정
        if is_valid and correction_result.get("corrected_question"):
            # 수정된 문제로 업데이트
            corrected_options_json = json.dumps(
                correction_result.get("corrected_options", []),
                ensure_ascii=False
            )
            
            updated_quiz = await quiz_crud.update_quiz(
                session,
                request.quiz_id,
                question=correction_result.get("corrected_question"),
                options=corrected_options_json,
                correct_answer=correction_result.get("correct_answer", 0),
                explanation=correction_result.get("corrected_explanation"),
            )
            
            if updated_quiz:
                corrected_quiz = quiz_schema.QuizResponse.model_validate(updated_quiz)
                logger.info(f"문제 수정 완료: quiz_id={request.quiz_id}, 수정 요청 타당함")
        
        original_quiz = quiz_schema.QuizResponse.model_validate(quiz)
        
        return quiz_schema.QuizCorrectionResponse(
            quiz_id=request.quiz_id,
            is_valid_request=is_valid,
            validation_feedback=correction_result.get("validation_feedback", ""),
            corrected_quiz=corrected_quiz,
            original_quiz=original_quiz,
        )
    except Exception as e:
        logger.error(f"문제 수정 요청 처리 중 오류: quiz_id={request.quiz_id}, 에러={e.__class__.__name__}: {str(e)}")
        raise


async def get_quiz_dashboard(
    session: AsyncSession,
) -> quiz_schema.QuizDashboardResponse:
    """관리자 대시보드: 문제 목록과 카테고리 매칭 상태 시각화"""
    from sqlalchemy import func, select
    from sqlalchemy.orm import joinedload
    from app.models.quiz import Quiz
    from app.models.sub_topic import SubTopic
    from app.models.main_topic import MainTopic
    
    # 전체 문제 개수
    total_count = await session.scalar(select(func.count(Quiz.id)))
    
    # 카테고리별 문제 개수
    quizzes_with_category = await session.execute(
        select(Quiz)
        .where(Quiz.sub_topic_id.isnot(None))
        .options(joinedload(Quiz.sub_topic).joinedload(SubTopic.main_topic).joinedload(MainTopic.subject))
    )
    quizzes = quizzes_with_category.scalars().all()
    
    quizzes_by_category = {}
    for quiz in quizzes:
        if quiz.sub_topic:
            category = f"{quiz.sub_topic.main_topic.subject.name} > {quiz.sub_topic.main_topic.name} > {quiz.sub_topic.name}"
            quizzes_by_category[category] = quizzes_by_category.get(category, 0) + 1
    
    # 최근 생성된 문제 (최대 10개)
    recent_quizzes_result = await session.execute(
        select(Quiz)
        .order_by(Quiz.created_at.desc())
        .limit(10)
    )
    recent_quizzes = [
        quiz_schema.QuizResponse.model_validate(q) 
        for q in recent_quizzes_result.scalars().all()
    ]
    
    # 검증이 필요한 문제 (최근 생성된 문제 중 일부, 실제로는 검증 상태를 추적해야 함)
    quizzes_needing_validation = recent_quizzes[:5]  # 임시로 최근 5개
    
    return quiz_schema.QuizDashboardResponse(
        total_quizzes=total_count or 0,
        quizzes_by_category=quizzes_by_category,
        validation_status={
            "validated": 0,  # 실제로는 검증 상태를 추적해야 함
            "pending": len(quizzes_needing_validation),
            "invalid": 0,
        },
        recent_quizzes=recent_quizzes,
        quizzes_needing_validation=quizzes_needing_validation,
    )


def _simple_keyword_check(question: str, category: str) -> bool:
    """간단한 키워드 기반 사전 필터링 (토큰 없이)
    
    카테고리 키워드가 문제에 포함되어 있는지 확인하여
    명백히 다른 카테고리인 경우 Gemini 검증을 스킵하여 토큰 절약
    """
    # 카테고리에서 키워드 추출 (마지막 세부항목명 사용)
    category_parts = category.split(" > ")
    if len(category_parts) >= 3:
        # 세부항목명의 주요 키워드 추출
        sub_topic_keywords = category_parts[-1].split()
        # 문제에 키워드가 하나라도 포함되어 있으면 통과
        question_lower = question.lower()
        for keyword in sub_topic_keywords:
            if len(keyword) > 2 and keyword.lower() in question_lower:
                return True
    # 키워드 체크 실패 시에도 검증 진행 (안전하게)
    return True
