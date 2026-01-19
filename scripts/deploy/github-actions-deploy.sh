#!/bin/bash
# GitHub Actions 배포 스크립트
# 사용법: ./scripts/deploy/github-actions-deploy.sh
# 
# 이 스크립트는 GitHub Actions에서만 사용되며,
# 환경변수는 GitHub Secrets에서 자동으로 주입됩니다.

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

export PROJECT_DIR ENV_FILE

echo "=== GitHub Actions 배포 시작 ==="
cd "$PROJECT_DIR" || exit 1

# 1. Git 코드 동기화
echo ""
echo "📦 [1/8] Git 코드 동기화 시작..."
if [ -f "${PROJECT_DIR}/scripts/utils/git-sync.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/git-sync.sh"
    "${PROJECT_DIR}/scripts/utils/git-sync.sh" || exit 1
else
    git fetch origin && git reset --hard origin/main && git clean -fd --exclude='data/postgres' || true
    echo "✅ 코드 동기화 완료"
fi

# 2. 환경변수 파일 확인
echo ""
echo "📝 [2/8] 환경변수 파일 확인 시작..."
if [ -f "${PROJECT_DIR}/scripts/env/ensure-env-file.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/env/ensure-env-file.sh"
    "${PROJECT_DIR}/scripts/env/ensure-env-file.sh" || exit 1
else
    [ ! -f "$ENV_FILE" ] && [ -f "${PROJECT_DIR}/env/.env.template" ] && cp "${PROJECT_DIR}/env/.env.template" "$ENV_FILE" && chmod 600 "$ENV_FILE" || true
    echo "✅ 환경변수 파일 확인 완료"
fi

# 3. BOM 제거
echo ""
echo "🔧 [3/8] BOM 제거 시작..."
if [ -f "${PROJECT_DIR}/scripts/utils/remove-bom.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/remove-bom.sh"
    "${PROJECT_DIR}/scripts/utils/remove-bom.sh" "$ENV_FILE" || exit 1
else
    echo "⚠️  BOM 제거 스크립트를 찾을 수 없습니다. 건너뜁니다."
fi

# 4. 환경변수 업데이트
echo ""
echo "🔄 [4/8] 환경변수 업데이트 시작..."
if [ -f "${PROJECT_DIR}/scripts/env/update-env.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/env/update-env.sh"
    "${PROJECT_DIR}/scripts/env/update-env.sh" || exit 1
else
    echo "⚠️  환경변수 업데이트 스크립트를 찾을 수 없습니다. 건너뜁니다."
fi

# 5. 환경변수 검증
echo ""
echo "✅ [5/8] 환경변수 검증 시작..."
if [ -f "${PROJECT_DIR}/scripts/env/verify-env.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/env/verify-env.sh"
    "${PROJECT_DIR}/scripts/env/verify-env.sh" || exit 1
else
    echo "⚠️  환경변수 검증 스크립트를 찾을 수 없습니다. 건너뜁니다."
fi

# 6. 데이터베이스 비밀번호 검증
echo ""
echo "🔐 [6/8] 데이터베이스 비밀번호 검증 시작..."
if [ -f "${PROJECT_DIR}/scripts/db/verify-db-password.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/verify-db-password.sh"
    "${PROJECT_DIR}/scripts/db/verify-db-password.sh" || exit 1
else
    echo "⚠️  데이터베이스 비밀번호 검증 스크립트를 찾을 수 없습니다. 건너뜁니다."
fi

# 7. 배포 스크립트 실행
echo ""
echo "🚀 [7/8] 배포 스크립트 실행 시작..."
if [ -f "${PROJECT_DIR}/scripts/deploy/deploy.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/deploy/deploy.sh"
    "${PROJECT_DIR}/scripts/deploy/deploy.sh" || exit 1
else
    echo "⚠️  배포 스크립트를 찾을 수 없습니다. 기본 배포 프로세스를 실행합니다."
    docker-compose --env-file "$ENV_FILE" down || true
    docker-compose --env-file "$ENV_FILE" build --no-cache
    docker-compose --env-file "$ENV_FILE" up -d
    sleep 10
    docker-compose --env-file "$ENV_FILE" exec -T app alembic upgrade head || exit 1
    echo "✅ 기본 배포 프로세스 완료"
fi

# 8. 헬스체크
echo ""
echo "🏥 [8/8] 헬스체크 시작..."
if [ -f "${PROJECT_DIR}/scripts/utils/health-check.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/health-check.sh"
    "${PROJECT_DIR}/scripts/utils/health-check.sh" "https://adsp-api.livbee.co.kr/health" 5 10 "$ENV_FILE" || exit 1
else
    echo "⚠️  헬스체크 스크립트를 찾을 수 없습니다. 건너뜁니다."
fi

echo ""
echo "=== 배포 완료 ==="
