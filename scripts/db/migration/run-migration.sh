#!/bin/bash
# 데이터베이스 마이그레이션 실행 스크립트
# 사용법: ./scripts/run-migration.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

cd "$PROJECT_DIR" || exit 1

source "$ENV_FILE"

echo "마이그레이션 실행 준비 중..."

if ! docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
    echo "애플리케이션 컨테이너가 실행 중이 아닙니다. 컨테이너를 시작합니다..."
    if [ -f "${PROJECT_DIR}/scripts/deploy/build-app.sh" ]; then
        chmod +x "${PROJECT_DIR}/scripts/deploy/build-app.sh"
        "${PROJECT_DIR}/scripts/deploy/build-app.sh" || exit 1
    else
        if [ -f "${PROJECT_DIR}/scripts/utils/docker/remove-containers.sh" ]; then
            chmod +x "${PROJECT_DIR}/scripts/utils/docker/remove-containers.sh"
            "${PROJECT_DIR}/scripts/utils/docker/remove-containers.sh" "adsp-quiz-backend"
        fi
        docker-compose --env-file "$ENV_FILE" build app
        docker-compose --env-file "$ENV_FILE" up -d --no-deps app
        echo "컨테이너 시작 대기 중..."
        sleep 5
    fi
fi

echo "컨테이너 안정화 대기 중..."
if [ -f "${PROJECT_DIR}/scripts/db/migration/wait-app-container.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/migration/wait-app-container.sh"
    "${PROJECT_DIR}/scripts/db/migration/wait-app-container.sh" || exit 1
else
    echo "⚠️  컨테이너 대기 스크립트를 찾을 수 없습니다."
    exit 1
fi

echo "마이그레이션 파일 확인 중..."
docker-compose --env-file "$ENV_FILE" exec -T app ls -la /app/migrations/versions/ || echo "⚠️  마이그레이션 파일 확인 실패"

echo "현재 DB revision 확인 중..."
docker-compose --env-file "$ENV_FILE" exec -T app alembic current || echo "⚠️  현재 revision 확인 실패 (초기 마이그레이션일 수 있음)"

echo "마이그레이션 히스토리 확인 중..."
docker-compose --env-file "$ENV_FILE" exec -T app alembic history || echo "⚠️  마이그레이션 히스토리 확인 실패"

echo "마이그레이션 실행 중..."
if docker-compose --env-file "$ENV_FILE" exec -T app alembic upgrade head; then
    echo "✅ 마이그레이션 완료"
    echo "업그레이드 후 revision 확인 중..."
    docker-compose --env-file "$ENV_FILE" exec -T app alembic current || echo "⚠️  revision 확인 실패"
else
    echo "❌ 마이그레이션 실패"
    echo "컨테이너 로그:"
    docker-compose --env-file "$ENV_FILE" logs --tail=50 app
    echo "마이그레이션 파일 목록:"
    docker-compose --env-file "$ENV_FILE" exec -T app ls -la /app/migrations/versions/ || true
    exit 1
fi
