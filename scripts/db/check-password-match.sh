#!/bin/bash
# PostgreSQL 컨테이너 비밀번호 일치 확인 스크립트
# 사용법: ./scripts/db/check-password-match.sh [DB_PASSWORD]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/env/.env}"
DB_PASSWORD_FROM_ENV="${1}"

cd "$PROJECT_DIR" || exit 1

POSTGRES_PASSWORD_FROM_CONTAINER=$(docker-compose --env-file "$ENV_FILE" exec -T postgres env 2>/dev/null | grep "^POSTGRES_PASSWORD=" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")

if [ -n "$POSTGRES_PASSWORD_FROM_CONTAINER" ]; then
    echo "  - PostgreSQL 컨테이너 비밀번호: *** (확인됨)"
    
    if [ "$DB_PASSWORD_FROM_ENV" != "$POSTGRES_PASSWORD_FROM_CONTAINER" ]; then
        echo -e "${RED}❌ 비밀번호 불일치 감지!${NC}"
        echo "  - .env 파일의 DB_PASSWORD와 PostgreSQL 컨테이너의 POSTGRES_PASSWORD가 일치하지 않습니다."
        echo ""
        echo "🔧 조치 방법:"
        echo "  1. 서버의 PostgreSQL 컨테이너 비밀번호 확인:"
        echo "     docker exec adsp-quiz-postgres env | grep POSTGRES_PASSWORD"
        echo ""
        echo "  2. GitHub Secrets의 DB_PASSWORD를 서버 비밀번호와 일치하도록 업데이트"
        echo "     또는 서버의 .env 파일을 GitHub Secrets와 일치하도록 수정"
        echo ""
        echo "  3. PostgreSQL 컨테이너 재생성 (데이터 백업 필수):"
        echo "     cd /opt/adsp-quiz-backend"
        echo "     docker-compose stop postgres"
        echo "     docker-compose rm -f postgres"
        echo "     docker-compose up -d postgres"
        echo ""
        exit 1
    else
        echo -e "${GREEN}✅ 비밀번호 일치 확인됨${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL 컨테이너에서 비밀번호를 확인할 수 없습니다. 연결 테스트로 검증합니다.${NC}"
fi
