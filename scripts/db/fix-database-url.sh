#!/bin/bash
# DATABASE_URL localhost -> postgres 변환 스크립트
# 사용법: ./scripts/fix-database-url.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

cd "$PROJECT_DIR" || exit 1

source "$ENV_FILE"

if [[ "$DATABASE_URL" == *"localhost"* ]]; then
    DATABASE_URL_DOCKER="${DATABASE_URL//localhost/postgres}"
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL_DOCKER|g" "$ENV_FILE"
    export DATABASE_URL="$DATABASE_URL_DOCKER"
    
    if ! echo "$DATABASE_URL" | grep -qE '^postgresql(\+asyncpg)?://[^@]+@'; then
        echo "❌ DATABASE_URL 업데이트 후 형식 검증 실패"
        exit 1
    fi
    
    if docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
        if [ -f "${PROJECT_DIR}/scripts/utils/remove-containers.sh" ]; then
            chmod +x "${PROJECT_DIR}/scripts/utils/remove-containers.sh"
            "${PROJECT_DIR}/scripts/utils/remove-containers.sh" "app"
        fi
        docker-compose --env-file "$ENV_FILE" up -d --no-deps app || sleep 2 && docker-compose --env-file "$ENV_FILE" up -d --no-deps app
        sleep 5
    fi
fi
