#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""핵심 정보 조회 API 로컬 테스트 스크립트"""
import asyncio
import sys
from pathlib import Path

import httpx

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings


async def test_core_content_api(sub_topic_id: int = 1, base_url: str = "http://localhost:8001"):
    """핵심 정보 조회 API 테스트"""
    url = f"{base_url}/api/v1/core-content/{sub_topic_id}"
    
    print(f"\n{'='*60}")
    print(f"테스트: GET {url}")
    print(f"환경: {settings.environment}")
    print(f"{'='*60}\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            
            print(f"상태 코드: {response.status_code}")
            print(f"응답 헤더: {dict(response.headers)}")
            print(f"\n응답 바디:")
            print(response.text)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n[OK] 성공:")
                print(f"  - id: {data.get('id')}")
                print(f"  - name: {data.get('name')}")
                print(f"  - core_content: {data.get('core_content', 'None')[:50]}...")
                print(f"  - updated_at: {data.get('updated_at')}")
            elif response.status_code == 500:
                error_data = response.json()
                print(f"\n[ERROR] 서버 에러:")
                print(f"  - code: {error_data.get('code', 'N/A')}")
                print(f"  - detail: {error_data.get('detail', 'N/A')}")
                print(f"\n[INFO] 백엔드 로그를 확인하세요.")
            elif response.status_code == 404:
                error_data = response.json()
                print(f"\n[INFO] 404 응답 (데이터 없음 - 정상):")
                print(f"  - detail: {error_data.get('detail', 'N/A')}")
            else:
                error_data = response.json()
                print(f"\n[INFO] 응답:")
                print(f"  - code: {error_data.get('code', 'N/A')}")
                print(f"  - detail: {error_data.get('detail', 'N/A')}")
                
        except httpx.ConnectError:
            print(f"\n[ERROR] 연결 실패: {base_url}에 연결할 수 없습니다.")
            print(f"   백엔드 서버가 실행 중인지 확인하세요.")
            print(f"   실행 방법: uvicorn app.main:app --reload --port 8001")
        except Exception as e:
            print(f"\n[ERROR] 예외 발생: {e.__class__.__name__}: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="핵심 정보 조회 API 테스트")
    parser.add_argument("--sub-topic-id", type=int, default=1, help="세부항목 ID (기본값: 1)")
    parser.add_argument("--base-url", type=str, default="http://localhost:8001", help="API 기본 URL")
    
    args = parser.parse_args()
    
    asyncio.run(test_core_content_api(args.sub_topic_id, args.base_url))
