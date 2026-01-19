#!/bin/bash
# 데이터베이스 비밀번호 검증 스크립트
# 사용법: ./scripts/verify-db-password.sh

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"

echo -e "${YELLOW}=== 데이터베이스 비밀번호 검증 ===${NC}"

cd "$PROJECT_DIR" || {
    echo -e "${RED}❌ 프로젝트 디렉토리로 이동 실패: $PROJECT_DIR${NC}"
    exit 1
}

# PostgreSQL 컨테이너 시작 확인
if [ -f "${PROJECT_DIR}/scripts/db/start-postgres.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/start-postgres.sh"
    "${PROJECT_DIR}/scripts/db/start-postgres.sh" || exit 1
else
    if ! docker-compose --env-file "$ENV_FILE" ps postgres 2>/dev/null | grep -q "Up"; then
        echo -e "${YELLOW}⚠️  PostgreSQL 컨테이너가 실행 중이 아닙니다. 시작합니다...${NC}"
        docker-compose --env-file "$ENV_FILE" up -d postgres
        sleep 5
    fi
fi

# DB 정보 추출
if [ -f "${PROJECT_DIR}/scripts/db/extract-db-info.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/extract-db-info.sh"
    eval $("${PROJECT_DIR}/scripts/db/extract-db-info.sh")
    DB_USER_FROM_ENV="$DB_USER"
    DB_PASSWORD_FROM_ENV="$DB_PASSWORD"
else
    DB_USER_FROM_ENV=$(grep "^DB_USER=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    DB_PASSWORD_FROM_ENV=$(grep "^DB_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    DB_NAME=$(grep "^DATABASE_URL=" "$ENV_FILE" | sed -n 's/.*\/\([^?]*\).*/\1/p' | head -1)
    DB_NAME="${DB_NAME:-adsp_quiz_db}"
    
    if [ -z "$DB_USER_FROM_ENV" ] || [ -z "$DB_PASSWORD_FROM_ENV" ]; then
        echo -e "${RED}❌ .env 파일에서 DB_USER 또는 DB_PASSWORD를 찾을 수 없습니다.${NC}"
        exit 1
    fi
fi

echo "데이터베이스 연결 정보:"
echo "  - 사용자: $DB_USER_FROM_ENV"
echo "  - 데이터베이스: $DB_NAME"
echo "  - 비밀번호: *** (마스킹됨)"

# 비밀번호 일치 확인
if [ -f "${PROJECT_DIR}/scripts/db/check-password-match.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/check-password-match.sh"
    "${PROJECT_DIR}/scripts/db/check-password-match.sh" "$DB_PASSWORD_FROM_ENV" || exit 1
else
    POSTGRES_PASSWORD_FROM_CONTAINER=$(docker-compose --env-file "$ENV_FILE" exec -T postgres env 2>/dev/null | grep "^POSTGRES_PASSWORD=" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    
    if [ -n "$POSTGRES_PASSWORD_FROM_CONTAINER" ] && [ "$DB_PASSWORD_FROM_ENV" != "$POSTGRES_PASSWORD_FROM_CONTAINER" ]; then
        echo -e "${RED}❌ 비밀번호 불일치 감지!${NC}"
        echo "  - .env 파일의 DB_PASSWORD와 PostgreSQL 컨테이너의 POSTGRES_PASSWORD가 일치하지 않습니다."
        echo ""
        echo "🔧 조치 방법:"
        echo "  1. 서버의 PostgreSQL 컨테이너 비밀번호 확인:"
        echo "     docker exec adsp-quiz-postgres env | grep POSTGRES_PASSWORD"
        echo ""
        echo "  2. GitHub Secrets의 DB_PASSWORD를 서버 비밀번호와 일치하도록 업데이트"
        echo ""
        exit 1
    fi
fi

# 연결 테스트
if [ -f "${PROJECT_DIR}/scripts/db/test-db-connection.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/db/test-db-connection.sh"
    if "${PROJECT_DIR}/scripts/db/test-db-connection.sh" "$DB_USER_FROM_ENV" "$DB_NAME" 3 2; then
        echo -e "${GREEN}✅ 데이터베이스 연결 성공 (비밀번호 인증 통과)${NC}"
        exit 0
    else
        echo -e "${RED}❌ 데이터베이스 연결 실패 (비밀번호 인증 실패)${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ 연결 테스트 스크립트를 찾을 수 없습니다.${NC}"
    exit 1
fi
