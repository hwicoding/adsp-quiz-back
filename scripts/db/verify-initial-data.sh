#!/bin/bash
# 초기 데이터 검증 스크립트
# 사용법: ./scripts/db/verify-initial-data.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

cd "$PROJECT_DIR" || exit 1

source "$ENV_FILE"

echo "초기 데이터 검증 중..."

if ! docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
    echo "❌ 애플리케이션 컨테이너가 실행 중이 아닙니다."
    exit 1
fi

echo "주요항목 데이터 확인 중..."
MAIN_TOPICS_COUNT=$(docker-compose --env-file "$ENV_FILE" exec -T app python -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM main_topics'))
        count = result.scalar()
        print(count)

asyncio.run(check())
" 2>/dev/null || echo "0")

if [ "$MAIN_TOPICS_COUNT" -lt 8 ]; then
    echo "❌ 주요항목 데이터 부족: 예상 8개, 실제 ${MAIN_TOPICS_COUNT}개"
    exit 1
fi
echo "✅ 주요항목 데이터 확인 완료: ${MAIN_TOPICS_COUNT}개"

echo "세부항목 데이터 확인 중..."
SUB_TOPICS_COUNT=$(docker-compose --env-file "$ENV_FILE" exec -T app python -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM sub_topics'))
        count = result.scalar()
        print(count)

asyncio.run(check())
" 2>/dev/null || echo "0")

if [ "$SUB_TOPICS_COUNT" -lt 28 ]; then
    echo "❌ 세부항목 데이터 부족: 예상 28개, 실제 ${SUB_TOPICS_COUNT}개"
    exit 1
fi
echo "✅ 세부항목 데이터 확인 완료: ${SUB_TOPICS_COUNT}개"

echo "핵심 세부항목 존재 확인 중..."
SUB_TOPIC_1=$(docker-compose --env-file "$ENV_FILE" exec -T app python -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM sub_topics WHERE id = 1'))
        count = result.scalar()
        print(count)

asyncio.run(check())
" 2>/dev/null || echo "0")

SUB_TOPIC_2=$(docker-compose --env-file "$ENV_FILE" exec -T app python -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM sub_topics WHERE id = 2'))
        count = result.scalar()
        print(count)

asyncio.run(check())
" 2>/dev/null || echo "0")

if [ "$SUB_TOPIC_1" -ne 1 ] || [ "$SUB_TOPIC_2" -ne 1 ]; then
    echo "❌ 핵심 세부항목 누락: sub_topic_id=1 (${SUB_TOPIC_1}개), sub_topic_id=2 (${SUB_TOPIC_2}개)"
    exit 1
fi
echo "✅ 핵심 세부항목 확인 완료: sub_topic_id=1, 2 존재"

echo "✅ 초기 데이터 검증 완료"