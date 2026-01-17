#!/bin/bash
# .env 파일에서 DB 정보 추출 스크립트
# 사용법: ./scripts/extract-db-info.sh

set -e

ENV_FILE="${ENV_FILE:-/opt/adsp-quiz-backend/env/.env}"

DB_USER=$(grep "^DB_USER=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
DB_PASSWORD=$(grep "^DB_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
DB_NAME=$(grep "^DATABASE_URL=" "$ENV_FILE" | sed -n 's/.*\/\([^?]*\).*/\1/p' | head -1)
DB_NAME="${DB_NAME:-adsp_quiz_db}"

if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "❌ .env 파일에서 DB_USER 또는 DB_PASSWORD를 찾을 수 없습니다." >&2
    exit 1
fi

echo "DB_USER=$DB_USER"
echo "DB_PASSWORD=$DB_PASSWORD"
echo "DB_NAME=$DB_NAME"
