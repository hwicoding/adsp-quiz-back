#!/bin/bash
# 원격 서버 배포 스크립트
# 사용법: ./scripts/deploy/ssh/remote-deploy.sh

set -e

PROJECT_DIR="/opt/adsp-quiz-backend"
ENV_FILE="${PROJECT_DIR}/env/.env"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "📦 프로젝트 디렉토리 생성 중..."
  sudo mkdir -p "$PROJECT_DIR"
  sudo chown -R ${USER}:${USER} "$PROJECT_DIR" || true
fi

cd "$PROJECT_DIR" || exit 1

if [ ! -d ".git" ]; then
  echo "📦 Git 저장소 초기화 중..."
  git init || true
  git remote add origin https://github.com/EHWIYA/adsp-quiz-back.git || git remote set-url origin https://github.com/EHWIYA/adsp-quiz-back.git || true
fi

echo "📦 [0/8] Git 코드 동기화 시작..."
git fetch origin || true
git reset --hard origin/main || true
git clean -fd --exclude='data/postgres' || true
echo "✅ 코드 동기화 완료"

export DATABASE_URL="${DATABASE_URL}"
export DB_USER="${DB_USER}"
export DB_PASSWORD="${DB_PASSWORD}"
export GEMINI_API_KEY="${GEMINI_API_KEY:-}"
export GEMINI_MAX_CONCURRENT="${GEMINI_MAX_CONCURRENT:-2}"
export SECRET_KEY="${SECRET_KEY}"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS}"
export ENV_FILE PROJECT_DIR

echo "📝 [0.5/8] .env 파일 업데이트 중..."
# env 디렉토리 생성
mkdir -p "$(dirname "$ENV_FILE")"

# 기존 .env 파일 백업
if [ -f "$ENV_FILE" ]; then
  cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)" || true
fi

# DATABASE_URL의 localhost를 postgres로 자동 변환 (Docker Compose 네트워크용)
if echo "$DATABASE_URL" | grep -q "@localhost\|@127\.0\.0\.1"; then
  echo "🔄 DATABASE_URL의 localhost를 postgres로 변환 중..."
  DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/@localhost/@postgres/g' | sed 's/@127\.0\.0\.1/@postgres/g')
fi

# GitHub Actions에서 받은 환경변수로 .env 파일 생성
cat > "$ENV_FILE" <<EOF
# Database
DATABASE_URL=${DATABASE_URL}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# Gemini API
GEMINI_API_KEY=${GEMINI_API_KEY}
GEMINI_MAX_CONCURRENT=${GEMINI_MAX_CONCURRENT:-2}

# Security
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256

# CORS
ALLOWED_ORIGINS=${ALLOWED_ORIGINS}

# Environment
ENVIRONMENT=${ENVIRONMENT:-production}
PORT=${PORT:-8001}
EOF

# .env 파일 권한 설정
chmod 600 "$ENV_FILE" || true
echo "✅ .env 파일 업데이트 완료"

# 실행 중인 컨테이너가 있으면 재시작하여 새 환경변수 적용
if docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
  echo "🔄 실행 중인 컨테이너 재시작 중 (환경변수 업데이트 반영)..."
  docker-compose --env-file "$ENV_FILE" restart app || true
  sleep 3
fi

# 환경변수 검증
echo "🔍 환경변수 검증 중..."
if [ -z "$DATABASE_URL" ]; then
  echo "❌ DATABASE_URL이 설정되지 않았습니다."
  exit 1
fi

if ! echo "$DATABASE_URL" | grep -qE '^postgresql(\+asyncpg)?://[^@]+@'; then
  echo "❌ DATABASE_URL 형식이 올바르지 않습니다: $DATABASE_URL"
  exit 1
fi

if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
  echo "❌ DB_USER 또는 DB_PASSWORD가 설정되지 않았습니다."
  exit 1
fi

if [ -z "$SECRET_KEY" ]; then
  echo "❌ SECRET_KEY가 설정되지 않았습니다."
  exit 1
fi

echo "✅ 환경변수 검증 완료"

if [ -f "${PROJECT_DIR}/scripts/deploy/github-actions-deploy.sh" ]; then
  chmod +x "${PROJECT_DIR}/scripts/deploy/github-actions-deploy.sh"
  "${PROJECT_DIR}/scripts/deploy/github-actions-deploy.sh" || exit 1
else
  echo "❌ GitHub Actions 배포 스크립트를 찾을 수 없습니다."
  echo "현재 디렉토리: $(pwd)"
  echo "스크립트 경로: ${PROJECT_DIR}/scripts/deploy/github-actions-deploy.sh"
  ls -la "${PROJECT_DIR}/scripts/deploy/" 2>/dev/null || echo "scripts/deploy 디렉토리가 존재하지 않습니다."
  exit 1
fi
