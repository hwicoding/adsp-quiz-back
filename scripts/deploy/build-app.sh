#!/bin/bash
# 애플리케이션 빌드 및 시작 스크립트
# 사용법: ./scripts/build-app.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

cd "$PROJECT_DIR" || exit 1

echo "기존 서비스 중지 및 컨테이너 제거 중..."
# docker-compose down으로 먼저 정리
docker-compose --env-file "$ENV_FILE" down || true

# 모든 관련 컨테이너 완전 제거 (ContainerConfig 오류 방지)
if [ -f "${PROJECT_DIR}/scripts/utils/docker/remove-containers.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/docker/remove-containers.sh"
    "${PROJECT_DIR}/scripts/utils/docker/remove-containers.sh" "adsp-quiz-backend"
    "${PROJECT_DIR}/scripts/utils/docker/remove-containers.sh" "adsp-quiz-postgres"
fi

# 네트워크 정리 (선택적)
docker network prune -f 2>/dev/null || true

echo "마이그레이션 파일 확인 중..."
if [ ! -f "${PROJECT_DIR}/migrations/versions/d4e5f6a7b8c9_add_initial_main_topics_and_sub_topics.py" ]; then
    echo "⚠️  마이그레이션 파일이 없습니다: d4e5f6a7b8c9_add_initial_main_topics_and_sub_topics.py"
    echo "Git 저장소 동기화 확인 중..."
    git fetch origin || true
    git reset --hard origin/main || true
    if [ ! -f "${PROJECT_DIR}/migrations/versions/d4e5f6a7b8c9_add_initial_main_topics_and_sub_topics.py" ]; then
        echo "❌ 마이그레이션 파일을 찾을 수 없습니다. 배포를 중단합니다."
        exit 1
    fi
fi
echo "✅ 마이그레이션 파일 확인 완료"

echo "기존 Docker 이미지 제거 중..."
docker-compose --env-file "$ENV_FILE" down || true
docker rmi $(docker images -q adsp-quiz-backend_app 2>/dev/null) 2>/dev/null || true

echo "Docker 이미지 빌드 중 (캐시 무시)..."
# 마이그레이션 파일 변경 시 캐시 문제 방지를 위해 --no-cache 사용
docker-compose --env-file "$ENV_FILE" build --no-cache app

echo "애플리케이션 컨테이너 시작 중..."
docker-compose --env-file "$ENV_FILE" up -d

echo "컨테이너 시작 대기 중..."
sleep 3

echo "컨테이너 내 마이그레이션 파일 검증 중..."
if docker-compose --env-file "$ENV_FILE" exec -T app test -f /app/migrations/versions/d4e5f6a7b8c9_add_initial_main_topics_and_sub_topics.py; then
    echo "✅ 마이그레이션 파일이 컨테이너에 정상적으로 복사되었습니다"
else
    echo "❌ 마이그레이션 파일이 컨테이너에 없습니다. 빌드를 다시 확인하세요."
    echo "컨테이너 내 마이그레이션 파일 목록:"
    docker-compose --env-file "$ENV_FILE" exec -T app ls -la /app/migrations/versions/ || true
    exit 1
fi

if [ -f "${PROJECT_DIR}/scripts/deploy/docker/wait-container.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/deploy/docker/wait-container.sh"
    MAX_WAIT=30 "${PROJECT_DIR}/scripts/deploy/docker/wait-container.sh" || exit 1
else
    echo "⚠️  컨테이너 대기 스크립트를 찾을 수 없습니다."
    exit 1
fi

echo "데이터베이스 마이그레이션 실행 중..."
source "$ENV_FILE"
if [ -f "${PROJECT_DIR}/scripts/db/migration/run-migration.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/migration/run-migration.sh"
    "${PROJECT_DIR}/scripts/db/migration/run-migration.sh" || exit 1
else
    echo "⚠️  마이그레이션 스크립트를 찾을 수 없습니다. 직접 실행합니다..."
    docker-compose --env-file "$ENV_FILE" exec -T app alembic upgrade head || exit 1
fi
echo "✅ 마이그레이션 완료"
