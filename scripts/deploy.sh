#!/bin/bash
# ADsP Quiz Backend 배포 스크립트
# 사용법: ./scripts/deploy.sh

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 디렉토리
PROJECT_DIR="/opt/adsp-quiz-backend"
ENV_FILE="${PROJECT_DIR}/env/.env"

echo -e "${GREEN}=== ADsP Quiz Backend 배포 스크립트 ===${NC}"

# 1. 환경변수 파일 확인
echo -e "\n${YELLOW}[1/5] 환경변수 파일 확인${NC}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ 환경변수 파일이 없습니다: $ENV_FILE${NC}"
    echo -e "${YELLOW}템플릿 파일을 복사하여 생성하세요:${NC}"
    echo "  cp ${PROJECT_DIR}/env/.env.template ${ENV_FILE}"
    echo "  nano ${ENV_FILE}"
    exit 1
fi

# 환경변수 파일 권한 확인
if [ "$(stat -c %a "$ENV_FILE")" != "600" ]; then
    echo -e "${YELLOW}⚠️  환경변수 파일 권한을 600으로 설정합니다...${NC}"
    chmod 600 "$ENV_FILE"
fi

echo -e "${GREEN}✅ 환경변수 파일 확인 완료${NC}"

# BOM 제거 (UTF-8 BOM이 있으면 제거)
if [ -f "$ENV_FILE" ]; then
    # BOM 제거 (sed를 사용하여 첫 3바이트가 EF BB BF인 경우 제거)
    sed -i '1s/^\xEF\xBB\xBF//' "$ENV_FILE" 2>/dev/null || true
    # 또는 Python을 사용하여 BOM 제거 (더 안전)
    if command -v python3 &> /dev/null; then
        python3 -c "
import sys
with open('$ENV_FILE', 'rb') as f:
    content = f.read()
if content.startswith(b'\xef\xbb\xbf'):
    with open('$ENV_FILE', 'wb') as f:
        f.write(content[3:])
" 2>/dev/null || true
    fi
fi

# 2. 필수 환경변수 확인
echo -e "\n${YELLOW}[2/5] 필수 환경변수 확인${NC}"
source "$ENV_FILE"

REQUIRED_VARS=("DATABASE_URL" "GEMINI_API_KEY" "SECRET_KEY" "ALLOWED_ORIGINS")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ 필수 환경변수가 설정되지 않았습니다:${NC}"
    printf '%s\n' "${MISSING_VARS[@]}"
    exit 1
fi

echo -e "${GREEN}✅ 필수 환경변수 확인 완료${NC}"

# 3. 데이터베이스 마이그레이션
echo -e "\n${YELLOW}[3/5] 데이터베이스 마이그레이션 실행${NC}"
cd "$PROJECT_DIR"

if docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-postgres.*Up"; then
    echo -e "${GREEN}✅ PostgreSQL 컨테이너 실행 중${NC}"
    
    # 마이그레이션 실행
    if docker-compose --env-file "$ENV_FILE" exec -T app alembic upgrade head; then
        echo -e "${GREEN}✅ 마이그레이션 완료${NC}"
    else
        echo -e "${RED}❌ 마이그레이션 실패${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL 컨테이너가 실행되지 않았습니다. 먼저 시작합니다...${NC}"
    docker-compose --env-file "$ENV_FILE" up -d postgres
    sleep 5
    docker-compose --env-file "$ENV_FILE" exec -T app alembic upgrade head
    echo -e "${GREEN}✅ 마이그레이션 완료${NC}"
fi

# 4. 애플리케이션 배포
echo -e "\n${YELLOW}[4/5] 애플리케이션 배포${NC}"

# 기존 컨테이너 중지
docker-compose --env-file "$ENV_FILE" down

# 새로 빌드 및 시작
docker-compose --env-file "$ENV_FILE" build --no-cache
docker-compose --env-file "$ENV_FILE" up -d

# 컨테이너 상태 확인
sleep 3
if docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
    echo -e "${GREEN}✅ 애플리케이션 컨테이너 실행 중${NC}"
else
    echo -e "${RED}❌ 애플리케이션 컨테이너 시작 실패${NC}"
    docker-compose --env-file "$ENV_FILE" logs app
    exit 1
fi

# 5. 헬스체크
echo -e "\n${YELLOW}[5/5] 헬스체크${NC}"
sleep 5

HEALTH_URL="https://adsp-api.livbee.co.kr/health"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")

if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ 헬스체크 성공 (HTTP $HEALTH_RESPONSE)${NC}"
    curl -s "$HEALTH_URL" | jq '.' 2>/dev/null || curl -s "$HEALTH_URL"
else
    echo -e "${YELLOW}⚠️  헬스체크 응답: HTTP $HEALTH_RESPONSE${NC}"
    echo -e "${YELLOW}애플리케이션 로그를 확인하세요:${NC}"
    echo "  docker-compose --env-file $ENV_FILE logs app"
fi

echo -e "\n${GREEN}=== 배포 완료 ===${NC}"
echo -e "${GREEN}애플리케이션 URL: https://adsp-api.livbee.co.kr${NC}"
echo -e "${GREEN}헬스체크 URL: https://adsp-api.livbee.co.kr/health${NC}"
