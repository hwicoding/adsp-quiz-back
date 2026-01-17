#!/bin/bash
# ADsP Quiz Backend 배포 스크립트
# 사용법: ./scripts/deploy.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

export PROJECT_DIR ENV_FILE

echo "=== ADsP Quiz Backend 배포 스크립트 ==="

# 0. 프로젝트 디렉토리 확인
if [ -f "${PROJECT_DIR}/scripts/utils/check-project-dir.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/check-project-dir.sh"
    "${PROJECT_DIR}/scripts/utils/check-project-dir.sh"
fi

# 1. 환경변수 파일 확인
if [ -f "${PROJECT_DIR}/scripts/env/check-env-file.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/env/check-env-file.sh"
    "${PROJECT_DIR}/scripts/env/check-env-file.sh"
fi

# BOM 제거
if [ -f "${PROJECT_DIR}/scripts/utils/remove-bom.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/remove-bom.sh"
    "${PROJECT_DIR}/scripts/utils/remove-bom.sh" "$ENV_FILE"
fi

# 2. 필수 환경변수 확인
if [ -f "${PROJECT_DIR}/scripts/env/verify-env.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/env/verify-env.sh"
    "${PROJECT_DIR}/scripts/env/verify-env.sh"
fi

source "$ENV_FILE"

# DATABASE_URL 수정 (localhost -> postgres)
if [ -f "${PROJECT_DIR}/scripts/db/fix-database-url.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/fix-database-url.sh"
    "${PROJECT_DIR}/scripts/db/fix-database-url.sh"
    source "$ENV_FILE"
fi

# 3. 데이터베이스 마이그레이션
if [ -f "${PROJECT_DIR}/scripts/db/start-postgres.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/start-postgres.sh"
    "${PROJECT_DIR}/scripts/db/start-postgres.sh"
fi

if [ -f "${PROJECT_DIR}/scripts/db/run-migration.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/run-migration.sh"
    "${PROJECT_DIR}/scripts/db/run-migration.sh"
fi

# 4. 애플리케이션 배포
if [ -f "${PROJECT_DIR}/scripts/deploy/build-app.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/deploy/build-app.sh"
    "${PROJECT_DIR}/scripts/deploy/build-app.sh"
fi

# 5. 헬스체크
if [ -f "${PROJECT_DIR}/scripts/utils/health-check.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/health-check.sh"
    "${PROJECT_DIR}/scripts/utils/health-check.sh" "https://adsp-api.livbee.co.kr/health" 1 5 "$ENV_FILE" || true
fi

echo "=== 배포 완료 ==="
