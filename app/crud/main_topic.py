from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.main_topic import MainTopic

# ADsP 전용 구조: subject_id는 항상 1 (ADsP)
ADSP_SUBJECT_ID = 1


async def get_main_topic_by_id(session: AsyncSession, main_topic_id: int) -> MainTopic | None:
    """ID로 주요항목 조회"""
    result = await session.execute(select(MainTopic).where(MainTopic.id == main_topic_id))
    return result.scalar_one_or_none()


async def get_all_main_topics(session: AsyncSession) -> Sequence[MainTopic]:
    """모든 주요항목 조회 (ADsP 전용)"""
    result = await session.execute(
        select(MainTopic)
        .where(MainTopic.subject_id == ADSP_SUBJECT_ID)
        .order_by(MainTopic.id)
    )
    return result.scalars().all()


async def get_main_topics_by_subject_id(session: AsyncSession, subject_id: int) -> Sequence[MainTopic]:
    """과목 ID로 주요항목 목록 조회 (하위 호환성 유지, 내부적으로는 ADsP만 사용)"""
    if subject_id != ADSP_SUBJECT_ID:
        return []
    return await get_all_main_topics(session)
