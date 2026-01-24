import logging
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import quiz as quiz_crud, subject as subject_crud, sub_topic as sub_topic_crud, quiz_validation as validation_crud
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
from app.utils.similarity import calculate_question_similarity

logger = logging.getLogger(__name__)

# 검증 점수 기준점 (0.7 = 70점)
# 이 값 이상이면 is_valid=true, 미만이면 false
VALIDATION_SCORE_THRESHOLD = 0.7


async def _create_quiz_response_with_status(
    session: AsyncSession,
    quiz,
) -> quiz_schema.QuizResponse:
    """Quiz 모델을 QuizResponse로 변환하며 validation_status 포함"""
    validation_statuses = await validation_crud.get_latest_validation_statuses(session, [quiz.id])
    validation_status = validation_statuses.get(quiz.id, "pending")
    
    quiz_dict = {
        "id": quiz.id,
        "subject_id": quiz.subject_id,
        "question": quiz.question,
        "options": quiz.options,
        "correct_answer": quiz.correct_answer,
        "explanation": quiz.explanation,
        "source_url": quiz.source_url,
        "created_at": quiz.created_at,
        "validation_status": validation_status,
    }
    return quiz_schema.QuizResponse.model_validate(quiz_dict)


async def _create_quiz_responses_with_status(
    session: AsyncSession,
    quizzes: list,
) -> list[quiz_schema.QuizResponse]:
    """여러 Quiz 모델을 QuizResponse 리스트로 변환하며 validation_status 포함 (일괄 조회)"""
    if not quizzes:
        return []
    
    quiz_ids = [q.id for q in quizzes]
    validation_statuses = await validation_crud.get_latest_validation_statuses(session, quiz_ids)
    
    quiz_responses = []
    for quiz in quizzes:
        validation_status = validation_statuses.get(quiz.id, "pending")
        quiz_dict = {
            "id": quiz.id,
            "subject_id": quiz.subject_id,
            "question": quiz.question,
            "options": quiz.options,
            "correct_answer": quiz.correct_answer,
            "explanation": quiz.explanation,
            "source_url": quiz.source_url,
            "created_at": quiz.created_at,
            "validation_status": validation_status,
        }
        quiz_responses.append(quiz_schema.QuizResponse.model_validate(quiz_dict))
    
    return quiz_responses


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
        return await _create_quiz_response_with_status(session, existing_quiz)

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

    return await _create_quiz_response_with_status(session, new_quiz)


async def generate_study_quizzes(
    session: AsyncSession,
    request: quiz_schema.StudyModeQuizCreateRequest,
) -> quiz_schema.StudyModeQuizListResponse:
    """학습 모드 문제 생성 (10개 일괄 생성, 캐싱 지원, 적정선 기준, 변형 적용, ADsP 전용)
    
    재시도 초과 시 새 문제 생성을 중단하고 캐시된 문제만 제공합니다.
    핵심 정보가 변경된 경우에만 새 문제 생성을 재시도합니다.
    """
    # 세부항목 존재 확인
    sub_topic = await sub_topic_crud.get_sub_topic_with_core_content(session, request.sub_topic_id)
    if not sub_topic:
        raise SubTopicNotFoundError(request.sub_topic_id)
    
    # 핵심 정보 확인
    if not sub_topic.core_content:
        raise InvalidQuizRequestError(f"세부항목에 핵심 정보가 없습니다: {request.sub_topic_id}")
    
    # 핵심 정보 변경 감지: 가장 최근 문제 생성 시점과 비교
    latest_quiz = await quiz_crud.get_latest_quiz_by_sub_topic_id(session, request.sub_topic_id)
    core_content_updated = False
    if latest_quiz:
        # 세부항목의 updated_at이 가장 최근 문제의 created_at보다 늦으면 핵심 정보 변경
        if sub_topic.updated_at and latest_quiz.created_at:
            core_content_updated = sub_topic.updated_at > latest_quiz.created_at
    else:
        # 문제가 없으면 핵심 정보가 새로 추가된 것으로 간주
        core_content_updated = True
    
    # 세부항목별 전체 문제 개수 확인 (적정선 기준 판단용)
    total_cached_count = await quiz_crud.get_quiz_count_by_sub_topic_id(
        session,
        request.sub_topic_id
    )
    
    # 적정선 기준에 따른 캐시/신규 비율 결정
    if total_cached_count >= 30:
        # 충분한 문제 풀 → 새로 생성 안 함
        cached_count = request.quiz_count
        new_count = 0
        logger.info(
            f"충분한 문제 풀: sub_topic_id={request.sub_topic_id}, "
            f"캐시={total_cached_count}개, 새로 생성 안 함"
        )
    elif total_cached_count >= 20:
        # 여유 있음 → 9:1 비율
        cached_count = 9
        new_count = 1
        logger.info(
            f"여유 있는 문제 풀: sub_topic_id={request.sub_topic_id}, "
            f"캐시={total_cached_count}개, 비율=9:1"
        )
    elif total_cached_count >= 10:
        # 적정 수준 → 8:2 비율
        cached_count = 8
        new_count = 2
        logger.info(
            f"적정 문제 풀: sub_topic_id={request.sub_topic_id}, "
            f"캐시={total_cached_count}개, 비율=8:2"
        )
    else:
        # 부족 → 부족한 개수만 새로 생성
        cached_count = total_cached_count
        new_count = request.quiz_count - total_cached_count
        logger.info(
            f"부족한 문제 풀: sub_topic_id={request.sub_topic_id}, "
            f"캐시={total_cached_count}개, 신규 생성={new_count}개"
        )
    
    # 캐시된 문제 조회 (유사 문제 제외 로직 포함)
    cached_quizzes_raw = await quiz_crud.get_quizzes_by_sub_topic_id(
        session,
        request.sub_topic_id,
        cached_count * 2  # 유사도 필터링을 위해 여유있게 조회
    )
    
    # 유사 문제 제외 (캐시 조회 시)
    cached_quizzes = []
    selected_questions = []
    for quiz in cached_quizzes_raw:
        if len(cached_quizzes) >= cached_count:
            break
        
        # 이미 선택한 문제와 유사도 체크
        is_similar = False
        for selected_q in selected_questions:
            similarity = _calculate_question_similarity(quiz.question, selected_q)
            if similarity >= 0.7:  # 70% 이상 유사하면 제외
                is_similar = True
                break
        
        if not is_similar:
            cached_quizzes.append(quiz)
            selected_questions.append(quiz.question)
    
    # 캐시된 문제가 부족한 경우 부족한 만큼만 사용
    actual_cached_count = len(cached_quizzes)
    if actual_cached_count < cached_count:
        new_count += cached_count - actual_cached_count
        logger.info(
            f"캐시 부족으로 신규 생성 증가: sub_topic_id={request.sub_topic_id}, "
            f"캐시={actual_cached_count}개, 신규={new_count}개"
        )
    
    # 부족한 문제 개수 계산
    needed_count = new_count
    
    # 핵심 정보가 변경되지 않았고 문제가 충분하면 새 문제 생성 안 함
    if needed_count > 0 and not core_content_updated and total_cached_count >= 10:
        logger.info(
            f"핵심 정보 변경 없음, 새 문제 생성 중단: sub_topic_id={request.sub_topic_id}, "
            f"캐시={total_cached_count}개, 핵심 정보 변경={core_content_updated}"
        )
        needed_count = 0
    
    if needed_count > 0:
        logger.info(
            f"새 문제 생성 필요: sub_topic_id={request.sub_topic_id}, "
            f"요청={request.quiz_count}, 캐시={actual_cached_count}, 생성={needed_count}, "
            f"핵심 정보 변경={core_content_updated}"
        )
    
    # 새 문제 생성
    new_quizzes = []
    # 유사 문제로 판단되어 변형이 필요한 문제 ID 목록
    similar_quiz_ids_to_vary = set()
    # ADsP 전용 구조: subject_id는 항상 1
    subject_id = 1
    # 유사도 재시도 제한 (문제당 최대 3회)
    MAX_SIMILARITY_RETRIES = 3
    # 문제 생산 중단 여부 (재시도 초과 시)
    production_stopped = False
    
    for i in range(needed_count):
        retry_count = 0
        quiz_created = False
        
        try:
            while not quiz_created and retry_count <= MAX_SIMILARITY_RETRIES:
                # 핵심 정보를 기반으로 문제 생성 (모든 핵심 정보 종합 활용)
                # 구분자로 분리된 모든 핵심 정보를 조회
                core_contents = sub_topic_crud.parse_core_contents(sub_topic.core_content, sub_topic.source_type)
                
                # 모든 핵심 정보를 종합하여 문제 생성에 활용
                if core_contents:
                    # 각 핵심 정보를 명확히 구분하여 결합
                    combined_parts = []
                    for idx, item in enumerate(core_contents, 1):
                        source_type_label = "텍스트" if item["source_type"] == "text" else "YouTube URL"
                        combined_parts.append(f"[핵심 정보 {idx} - {source_type_label}]\n{item['core_content']}")
                    combined_content = "\n\n".join(combined_parts)
                else:
                    # 핵심 정보가 없는 경우 (이미 위에서 체크했지만 안전장치)
                    combined_content = sub_topic.core_content or ""
                
                # 모든 핵심 정보를 종합하여 문제 생성
                ai_request = ai.AIQuizGenerationRequest(
                    source_text=combined_content,
                    subject_name=sub_topic.main_topic.subject.name,
                    main_topic_name=sub_topic.main_topic.name,
                    sub_topic_name=sub_topic.name,
                )
                
                ai_response = await ai_service.generate_quiz(ai_request)
                
                # 유사 문제 체크 (토큰 없이)
                similar_quizzes = await quiz_crud.get_similar_quizzes_by_question(
                    session,
                    request.sub_topic_id,
                    ai_response.question,
                    similarity_threshold=0.7,
                    limit=5
                )
                
                if similar_quizzes:
                    retry_count += 1
                    logger.info(
                        f"유사 문제 발견 (재시도 {retry_count}/{MAX_SIMILARITY_RETRIES}): "
                        f"sub_topic_id={request.sub_topic_id}, "
                        f"유사 문제 개수={len(similar_quizzes)}, "
                        f"문제={ai_response.question[:50]}..."
                    )
                    
                    # 재시도 횟수 초과 시 처리
                    if retry_count > MAX_SIMILARITY_RETRIES:
                        # 핵심 정보가 변경되지 않았으면 새 문제 생성을 중단하고 캐시만 사용
                        if not core_content_updated:
                            logger.warning(
                                f"유사도 재시도 횟수 초과, 문제 생산 중단: "
                                f"sub_topic_id={request.sub_topic_id}, "
                                f"재시도 횟수={retry_count}, "
                                f"핵심 정보 변경 없음 → 캐시 문제만 사용"
                            )
                            production_stopped = True
                            quiz_created = True  # 새 문제 생성 중단
                            break  # while 루프 종료
                        else:
                            # 핵심 정보가 변경되었으면 유사 문제 변형하여 사용
                            similar_quiz = similar_quizzes[0]
                            new_quizzes.append(similar_quiz)
                            similar_quiz_ids_to_vary.add(similar_quiz.id)
                            quiz_created = True
                            logger.warning(
                                f"유사도 재시도 횟수 초과, 핵심 정보 변경 감지로 변형 사용: "
                                f"quiz_id={similar_quiz.id}, "
                                f"sub_topic_id={request.sub_topic_id}, "
                                f"재시도 횟수={retry_count} "
                                f"(나중에 변형 적용 단계에서 100% 확률로 변형)"
                            )
                    # 재시도 가능하면 continue
                    continue
                
                # 유사 문제가 없으면 정상 진행
                quiz_created = True
                
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
                            
                            if not validation_result.get("is_valid", False) or validation_result.get("validation_score", 0.0) < VALIDATION_SCORE_THRESHOLD:
                                logger.warning(
                                    f"자동 검증 실패: sub_topic_id={request.sub_topic_id}, "
                                    f"score={validation_result.get('validation_score', 0.0)}, "
                                    f"issues={validation_result.get('issues', [])}"
                                )
                    except Exception as e:
                        # 검증 실패해도 문제 생성은 계속 진행
                        logger.warning(f"자동 검증 중 오류 (문제 생성은 계속 진행): {e.__class__.__name__}: {str(e)}")
                
                # 해시 생성 (핵심 정보 + 인덱스 + 재시도 횟수로 고유성 보장)
                source_hash = youtube_service.generate_hash(
                    f"{sub_topic.core_content}_{request.sub_topic_id}_{i}_{retry_count}"
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
                    quiz_created = True
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
                    f"문제: {ai_response.question[:50]}... "
                    f"(재시도 횟수: {retry_count})"
                )
            
            # 문제 생산이 중단된 경우 루프 종료
            if production_stopped:
                logger.info(
                    f"문제 생산 중단으로 루프 종료: sub_topic_id={request.sub_topic_id}, "
                    f"생성된 문제: {len(new_quizzes)}/{needed_count}"
                )
                break
            
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
    
    # 캐시된 문제에 변형 적용 (토큰 없이)
    quiz_responses = []
    for quiz in all_quizzes[:request.quiz_count]:
        quiz_response = quiz_schema.QuizResponse.model_validate(quiz)
        
        # 유사 문제로 판단된 경우 100% 확률로 변형, 그 외는 70% 확률로 변형
        should_vary = quiz.id in similar_quiz_ids_to_vary or random.random() < 0.7
        if should_vary:
            quiz_response = quiz_variation.vary_quiz(quiz_response)
            if quiz.id in similar_quiz_ids_to_vary:
                logger.info(
                    f"유사 문제 변형 적용: quiz_id={quiz.id}, "
                    f"sub_topic_id={request.sub_topic_id}"
                )
            else:
                logger.debug(
                    f"캐시 문제 변형 적용: quiz_id={quiz.id}, "
                    f"sub_topic_id={request.sub_topic_id}"
                )
        
        # validation_status 포함
        validation_statuses = await validation_crud.get_latest_validation_statuses(session, [quiz.id])
        validation_status = validation_statuses.get(quiz.id, "pending")
        
        quiz_dict = quiz_response.model_dump()
        quiz_dict["validation_status"] = validation_status
        quiz_responses.append(quiz_schema.QuizResponse.model_validate(quiz_dict))
    
    logger.info(
        f"학습 모드 문제 생성 완료: sub_topic_id={request.sub_topic_id}, "
        f"요청={request.quiz_count}, 반환={len(quiz_responses)} "
        f"(캐시={actual_cached_count}, 신규={len(new_quizzes)}, 변형 적용)"
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
        quiz_response = await _create_quiz_response_with_status(session, existing_quiz)
        
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
        # 핵심 정보를 기반으로 문제 생성 (모든 핵심 정보 종합 활용)
        # 구분자로 분리된 모든 핵심 정보를 조회
        core_contents = sub_topic_crud.parse_core_contents(sub_topic.core_content, sub_topic.source_type)
        
        # 모든 핵심 정보를 종합하여 문제 생성에 활용
        if core_contents:
            # 각 핵심 정보를 명확히 구분하여 결합
            combined_parts = []
            for idx, item in enumerate(core_contents, 1):
                source_type_label = "텍스트" if item["source_type"] == "text" else "YouTube URL"
                combined_parts.append(f"[핵심 정보 {idx} - {source_type_label}]\n{item['core_content']}")
            combined_content = "\n\n".join(combined_parts)
        else:
            # 핵심 정보가 없는 경우 (이미 위에서 체크했지만 안전장치)
            combined_content = sub_topic.core_content or ""
        
        # 모든 핵심 정보를 종합하여 문제 생성
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
                    
                    if not validation_result.get("is_valid", False) or validation_result.get("validation_score", 0.0) < VALIDATION_SCORE_THRESHOLD:
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
            quiz_response = await _create_quiz_response_with_status(session, existing_quiz)
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
        
        quiz_response = await _create_quiz_response_with_status(session, new_quiz)
        
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
    from app.crud import quiz_validation as validation_crud
    
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
        
        # 검증 결과 저장
        is_valid = validation_result.get("is_valid", False)
        validation_score = validation_result.get("validation_score", 0.0)
        
        # 점수와 is_valid의 일관성 검증
        if is_valid and validation_score < VALIDATION_SCORE_THRESHOLD:
            logger.warning(
                f"검증 결과 일관성 문제 감지: quiz_id={quiz_id}, "
                f"is_valid={is_valid}, validation_score={validation_score}. "
                f"is_valid=true인데 점수가 {VALIDATION_SCORE_THRESHOLD} 미만입니다. "
                f"점수에 맞춰 is_valid를 false로 조정합니다."
            )
            # 일관성을 위해 is_valid를 false로 조정
            is_valid = False
            validation_result["is_valid"] = False
        
        if not is_valid and validation_score >= VALIDATION_SCORE_THRESHOLD:
            logger.warning(
                f"검증 결과 일관성 문제 감지: quiz_id={quiz_id}, "
                f"is_valid={is_valid}, validation_score={validation_score}. "
                f"is_valid=false인데 점수가 {VALIDATION_SCORE_THRESHOLD} 이상입니다. "
                f"점수에 맞춰 is_valid를 true로 조정합니다."
            )
            # 일관성을 위해 is_valid를 true로 조정
            is_valid = True
            validation_result["is_valid"] = True
        
        validation_status = "valid" if is_valid else "invalid"
        validation_score_int = int(validation_score * 100) if validation_score else None
        
        await validation_crud.create_quiz_validation(
            session=session,
            quiz_id=quiz_id,
            validation_status=validation_status,
            validation_score=validation_score_int,
            feedback=validation_result.get("feedback", ""),
            issues=validation_result.get("issues", []),
        )
        
        return quiz_schema.QuizValidationResponse(
            quiz_id=quiz_id,
            is_valid=is_valid,
            category=category,
            validation_score=validation_score,
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
                corrected_quiz = await _create_quiz_response_with_status(session, updated_quiz)
                logger.info(f"문제 수정 완료: quiz_id={request.quiz_id}, 수정 요청 타당함")
        
        original_quiz = await _create_quiz_response_with_status(session, quiz)
        
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
    """관리자 대시보드: 문제 목록과 카테고리 매칭 상태 시각화
    
    카테고리별 상태:
    - normal: 정상 (문제 개수 충분, 문제 생산 가능)
    - insufficient: 부족 (문제 개수 10개 미만)
    - production_difficult: 생산 어려움 (재시도 초과로 문제 생산 중단 가능성)
    """
    from sqlalchemy import func, select
    from sqlalchemy.orm import joinedload
    from app.models.quiz import Quiz
    from app.models.sub_topic import SubTopic
    from app.models.main_topic import MainTopic
    from app.crud import quiz_validation as validation_crud, sub_topic as sub_topic_crud, main_topic as main_topic_crud
    
    # 전체 문제 개수
    total_count = await session.scalar(select(func.count(Quiz.id)))
    
    # 카테고리별 문제 개수 및 상태 조회
    quizzes_by_category = {}
    category_status = {}
    
    # 주요항목의 subject 관계를 eager load
    from sqlalchemy.orm import joinedload
    all_main_topics_with_subject = await session.execute(
        select(MainTopic)
        .options(joinedload(MainTopic.subject))
        .where(MainTopic.subject_id == 1)  # ADsP 전용
        .order_by(MainTopic.id)
    )
    main_topics_list = all_main_topics_with_subject.unique().scalars().all()
    
    for main_topic in main_topics_list:
        subject_name = main_topic.subject.name if main_topic.subject else "ADsP"
        
        sub_topics = await sub_topic_crud.get_sub_topics_by_main_topic_id(session, main_topic.id)
        for sub_topic in sub_topics:
            category = f"{subject_name} > {main_topic.name} > {sub_topic.name}"
            
            # 문제 개수 조회
            quiz_count = await quiz_crud.get_quiz_count_by_sub_topic_id(session, sub_topic.id)
            quizzes_by_category[category] = quiz_count
            
            # 카테고리 상태 판단
            status = "normal"
            if quiz_count < 10:
                status = "insufficient"  # 부족 (10개 미만)
            else:
                # 가장 최근 문제와 핵심 정보 업데이트 시점 비교
                latest_quiz = await quiz_crud.get_latest_quiz_by_sub_topic_id(session, sub_topic.id)
                if latest_quiz and sub_topic.updated_at and latest_quiz.created_at:
                    # 핵심 정보가 변경되지 않았고 문제가 충분하면 생산 어려움 가능성
                    # (재시도 초과로 생산 중단된 경우)
                    if sub_topic.updated_at <= latest_quiz.created_at:
                        # 핵심 정보가 오래 안 바뀌고 문제도 오래 안 생성되면 생산 어려움 가능성
                        # 하지만 정확한 감지는 어려우므로 일단 normal로 처리
                        # (향후 로그 분석 또는 플래그 추가로 개선 가능)
                        status = "normal"
                    else:
                        # 핵심 정보가 최근에 변경되었으면 정상
                        status = "normal"
                else:
                    # 문제가 없거나 정보가 부족하면 정상으로 간주
                    status = "normal"
            
            category_status[category] = status
    
    # 최근 생성된 문제 (최대 10개)
    recent_quizzes_result = await session.execute(
        select(Quiz)
        .order_by(Quiz.created_at.desc())
        .limit(10)
    )
    recent_quizzes_models = recent_quizzes_result.scalars().all()
    recent_quiz_ids = [q.id for q in recent_quizzes_models]
    
    # 검증 상태별 개수 조회
    validation_status_counts = await validation_crud.get_validation_status_counts(session)
    
    # 검증이 필요한 문제 ID 목록 조회
    quiz_ids_needing_validation = await validation_crud.get_quizzes_needing_validation(session)
    
    # 검증이 필요한 문제 상세 정보 조회
    if quiz_ids_needing_validation:
        quizzes_needing_validation_result = await session.execute(
            select(Quiz)
            .where(Quiz.id.in_(quiz_ids_needing_validation))
            .order_by(Quiz.created_at.desc())
        )
        quizzes_needing_validation_models = quizzes_needing_validation_result.scalars().all()
    else:
        quizzes_needing_validation_models = []
    
    # 모든 quiz_id에 대한 validation_status 일괄 조회
    all_quiz_ids = list(set(recent_quiz_ids + quiz_ids_needing_validation))
    validation_statuses = await validation_crud.get_latest_validation_statuses(session, all_quiz_ids)
    
    # recent_quizzes에 validation_status 추가
    recent_quizzes = []
    for q in recent_quizzes_models:
        quiz_dict = {
            "id": q.id,
            "subject_id": q.subject_id,
            "question": q.question,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "source_url": q.source_url,
            "created_at": q.created_at,
            "validation_status": validation_statuses.get(q.id, "pending"),
        }
        recent_quizzes.append(quiz_schema.QuizResponse.model_validate(quiz_dict))
    
    # quizzes_needing_validation에 validation_status 추가
    quizzes_needing_validation = []
    for q in quizzes_needing_validation_models:
        quiz_dict = {
            "id": q.id,
            "subject_id": q.subject_id,
            "question": q.question,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "source_url": q.source_url,
            "created_at": q.created_at,
            "validation_status": validation_statuses.get(q.id, "pending"),
        }
        quizzes_needing_validation.append(quiz_schema.QuizResponse.model_validate(quiz_dict))
    
    return quiz_schema.QuizDashboardResponse(
        total_quizzes=total_count or 0,
        quizzes_by_category=quizzes_by_category,
        category_status=category_status,
        validation_status=validation_status_counts,
        recent_quizzes=recent_quizzes,
        quizzes_needing_validation=quizzes_needing_validation,
    )


def _calculate_question_similarity(q1: str, q2: str) -> float:
    """문제 텍스트 유사도 계산 (토큰 없이, 정교한 방식)
    
    한국어 특성을 고려한 다중 유사도 지표 조합:
    - 정규화된 단어 Jaccard 유사도 (조사/어미 제거, 유사 표현 정규화)
    - 문자 n-gram 유사도 (2-gram, 3-gram)
    
    Args:
        q1: 첫 번째 문제 텍스트
        q2: 두 번째 문제 텍스트
    
    Returns:
        0.0 ~ 1.0 사이의 유사도 (1.0이 완전 동일)
    """
    return calculate_question_similarity(q1, q2)


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
