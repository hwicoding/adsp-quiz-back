#!/bin/bash
# 프로젝트 디렉토리 확인 스크립트
# 사용법: ./scripts/check-project-dir.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"

cd "$PROJECT_DIR" || {
    echo "❌ 프로젝트 디렉토리로 이동 실패: $PROJECT_DIR"
    exit 1
}

echo "현재 작업 디렉토리: $(pwd)"
if ls -la docker-compose*.yml 2>/dev/null; then
    echo "✅ docker-compose 파일 확인 완료"
else
    echo "⚠️  docker-compose 파일을 찾을 수 없습니다."
    ls -la
fi
