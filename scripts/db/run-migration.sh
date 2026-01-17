#!/bin/bash
# 데이터베이스 마이그레이션 실행 스크립트
# 사용법: ./scripts/run-migration.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

cd "$PROJECT_DIR" || exit 1

source "$ENV_FILE"

if ! docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
    if [ -f "${PROJECT_DIR}/scripts/utils/remove-containers.sh" ]; then
        chmod +x "${PROJECT_DIR}/scripts/utils/remove-containers.sh"
        "${PROJECT_DIR}/scripts/utils/remove-containers.sh" "adsp-quiz-backend"
    fi
    docker-compose --env-file "$ENV_FILE" build app
    docker-compose --env-file "$ENV_FILE" up -d --no-deps app
    sleep 5
fi

if docker-compose --env-file "$ENV_FILE" exec -T -e DATABASE_URL="$DATABASE_URL" app alembic upgrade head; then
    echo "✅ 마이그레이션 완료"
else
    echo "❌ 마이그레이션 실패"
    exit 1
fi
