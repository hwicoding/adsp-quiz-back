#!/bin/bash
# PostgreSQL 컨테이너 시작 및 대기 스크립트
# 사용법: ./scripts/start-postgres.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

cd "$PROJECT_DIR" || exit 1

source "$ENV_FILE" 2>/dev/null || true

if ! docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-postgres.*Up"; then
    docker-compose --env-file "$ENV_FILE" up -d postgres
    
    for i in {1..30}; do
        if docker-compose --env-file "$ENV_FILE" exec -T postgres pg_isready -U "${DB_USER:-postgres}" > /dev/null 2>&1; then
            echo "✅ PostgreSQL 준비 완료"
            exit 0
        fi
        [ $i -eq 30 ] && echo "❌ PostgreSQL 준비 시간 초과" && exit 1
        sleep 1
    done
fi
