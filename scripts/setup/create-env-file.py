#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""서버 담당자로부터 받은 .env 파일 내용으로 로컬 .env 파일 생성"""
import os
from pathlib import Path

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"

# 서버 담당자로부터 받은 .env 내용 (로컬 테스트용으로 호스트명 변경)
env_content = """# Database
# 로컬 테스트용: 호스트명을 localhost로 변경
DATABASE_URL=postgresql+asyncpg://adsp_quiz_user:oXRulAw4AwNBP1ERkg3lSOlBg@localhost:5432/adsp_quiz_db
DB_USER=adsp_quiz_user
DB_PASSWORD=oXRulAw4AwNBP1ERkg3lSOlBg

# OpenAI (서버에서 제공된 값, 필요시 업데이트)
OPENAI_API_KEY=sk-your-openai-api-key

# Security
SECRET_KEY=pzuMFg5YcqJ5PWI96RS1C7VMkNxpi8muI58Vo0xdCsw
ALGORITHM=HS256

# CORS
ALLOWED_ORIGINS=https://adsp.livbee.co.kr,http://localhost:5173

# Environment
# 로컬 개발 시 development로 변경하면 상세 에러 메시지 확인 가능
ENVIRONMENT=development
GEMINI_API_KEY=AIzaSyBjhEP0nEbAKOWRlt2HDm1FrIE7evXCN-E
PORT=8001
"""

def create_env_file():
    """.env 파일 생성 (UTF-8, BOM 없음)"""
    print(f"[INFO] .env 파일 생성 중: {env_file}")
    
    # 기존 파일이 있으면 백업
    if env_file.exists():
        backup_file = project_root / ".env.backup"
        print(f"[INFO] 기존 .env 파일 백업: {backup_file}")
        with open(env_file, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        with open(backup_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(backup_content)
    
    # .env 파일 생성 (UTF-8, BOM 없음, LF 줄바꿈)
    with open(env_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(env_content)
    
    print(f"[OK] .env 파일 생성 완료")
    print(f"[INFO] 파일 위치: {env_file}")
    print(f"[INFO] 파일 크기: {env_file.stat().st_size} bytes")
    
    # 파일 권한 확인 (Windows에서는 chmod가 없으므로 스킵)
    if os.name != 'nt':
        os.chmod(env_file, 0o600)
        print(f"[INFO] 파일 권한 설정: 600")


if __name__ == "__main__":
    try:
        create_env_file()
        print("\n[OK] 작업 완료")
    except Exception as e:
        print(f"\n[ERROR] 에러 발생: {e.__class__.__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
