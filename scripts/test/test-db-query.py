#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 직접 쿼리 테스트 스크립트"""
import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 환경변수 로드
from dotenv import load_dotenv
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # env 폴더 확인
    env_file = project_root / "env" / ".env"
    if env_file.exists():
        load_dotenv(env_file)

from sqlalchemy import select, text
from app.models.base import get_engine, get_async_session_maker
from app.models.sub_topic import SubTopic


async def test_db_query(sub_topic_id: int = 1):
    """DB에서 직접 세부항목 조회"""
    print(f"\n{'='*60}")
    print(f"DB 직접 쿼리 테스트: sub_topic_id={sub_topic_id}")
    print(f"{'='*60}\n")
    
    # DATABASE_URL 확인
    from app.core.config import settings
    if not settings.database_url:
        print(f"[ERROR] DATABASE_URL이 설정되지 않았습니다.")
        print(f"  .env 파일을 확인하거나 환경변수를 설정하세요.")
        return
    
    print(f"[INFO] DATABASE_URL: {settings.database_url[:50]}...")
    
    try:
        # 엔진 연결 테스트
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"[OK] DB 연결 성공: {result.scalar()}")
        
        # 세부항목 조회
        session_maker = get_async_session_maker()
        async with session_maker() as session:
            # 방법 1: ORM 사용
            print(f"\n[방법 1] ORM으로 조회:")
            result = await session.execute(
                select(SubTopic).where(SubTopic.id == sub_topic_id)
            )
            sub_topic = result.scalar_one_or_none()
            
            if sub_topic:
                print(f"[OK] 조회 성공:")
                print(f"  - id: {sub_topic.id}")
                print(f"  - name: {sub_topic.name}")
                print(f"  - main_topic_id: {sub_topic.main_topic_id}")
                print(f"  - core_content: {sub_topic.core_content[:50] if sub_topic.core_content else 'None'}...")
                print(f"  - created_at: {sub_topic.created_at}")
                print(f"  - updated_at: {sub_topic.updated_at}")
            else:
                print(f"[WARN] 레코드를 찾을 수 없습니다: sub_topic_id={sub_topic_id}")
            
            # 방법 2: Raw SQL 사용
            print(f"\n[방법 2] Raw SQL로 조회:")
            result = await session.execute(
                text("SELECT id, name, main_topic_id, core_content, created_at, updated_at FROM sub_topics WHERE id = :id"),
                {"id": sub_topic_id}
            )
            row = result.first()
            
            if row:
                print(f"[OK] 조회 성공:")
                print(f"  - id: {row[0]}")
                print(f"  - name: {row[1]}")
                print(f"  - main_topic_id: {row[2]}")
                print(f"  - core_content: {row[3][:50] if row[3] else 'None'}...")
            else:
                print(f"[WARN] 레코드를 찾을 수 없습니다: sub_topic_id={sub_topic_id}")
            
            # 테이블 존재 여부 확인
            print(f"\n[방법 3] 테이블 존재 여부 확인:")
            result = await session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'sub_topics'
                    )
                """)
            )
            table_exists = result.scalar()
            print(f"  - sub_topics 테이블 존재: {table_exists}")
            
            if table_exists:
                # 전체 레코드 수 확인
                result = await session.execute(text("SELECT COUNT(*) FROM sub_topics"))
                count = result.scalar()
                print(f"  - 전체 레코드 수: {count}")
                
                # ID 목록 확인
                result = await session.execute(text("SELECT id FROM sub_topics ORDER BY id LIMIT 10"))
                ids = [row[0] for row in result.fetchall()]
                print(f"  - 사용 가능한 ID 목록 (최대 10개): {ids}")
                
    except Exception as e:
        print(f"\n[ERROR] 에러 발생: {e.__class__.__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"\n[INFO] 가능한 원인:")
        print(f"  1. DB 연결 정보가 잘못되었습니다 (.env 파일 확인)")
        print(f"  2. DB 서버가 실행 중이지 않습니다")
        print(f"  3. 마이그레이션이 적용되지 않았습니다 (alembic upgrade head)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DB 직접 쿼리 테스트")
    parser.add_argument("--sub-topic-id", type=int, default=1, help="세부항목 ID (기본값: 1)")
    
    args = parser.parse_args()
    
    asyncio.run(test_db_query(args.sub_topic_id))
