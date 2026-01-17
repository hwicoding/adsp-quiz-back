#!/bin/bash
# 데이터베이스 연결 테스트 스크립트
# 사용법: ./scripts/test-db-connection.sh [DB_USER] [DB_NAME] [MAX_RETRIES] [RETRY_DELAY]

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"
DB_USER="${1}"
DB_NAME="${2:-adsp_quiz_db}"
MAX_RETRIES="${3:-3}"
RETRY_DELAY="${4:-2}"

cd "$PROJECT_DIR" || exit 1

for i in $(seq 1 $MAX_RETRIES); do
    if docker-compose --env-file "$ENV_FILE" exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ 데이터베이스 연결 성공"
        exit 0
    else
        if [ $i -eq $MAX_RETRIES ]; then
            echo "❌ 데이터베이스 연결 실패" >&2
            exit 1
        else
            sleep $RETRY_DELAY
        fi
    fi
done
