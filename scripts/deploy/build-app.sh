#!/bin/bash
# 애플리케이션 빌드 및 시작 스크립트
# 사용법: ./scripts/build-app.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

cd "$PROJECT_DIR" || exit 1

echo "기존 애플리케이션 컨테이너 중지 중..."
docker-compose --env-file "$ENV_FILE" stop app || true

if [ -f "${PROJECT_DIR}/scripts/utils/remove-containers.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/remove-containers.sh"
    "${PROJECT_DIR}/scripts/utils/remove-containers.sh" "adsp-quiz-backend"
fi

echo "Docker 이미지 빌드 중..."
docker-compose --env-file "$ENV_FILE" build --no-cache

echo "애플리케이션 컨테이너 시작 중..."
docker-compose --env-file "$ENV_FILE" up -d

echo "컨테이너 시작 대기 중..."
sleep 3

if docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
    echo "✅ 애플리케이션 컨테이너 실행 중"
else
    echo "❌ 애플리케이션 컨테이너 시작 실패"
    echo "컨테이너 로그:"
    docker-compose --env-file "$ENV_FILE" logs app
    exit 1
fi
