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

# 0. 프로젝트 루트 디렉토리로 이동 (필수)
echo -e "\n${YELLOW}[0/5] 프로젝트 디렉토리 확인${NC}"
cd "$PROJECT_DIR" || {
    echo -e "${RED}❌ 프로젝트 디렉토리로 이동 실패: $PROJECT_DIR${NC}"
    exit 1
}

echo "현재 작업 디렉토리: $(pwd)"
echo "docker-compose 파일 확인:"
if ls -la docker-compose*.yml 2>/dev/null; then
    echo -e "${GREEN}✅ docker-compose 파일 확인 완료${NC}"
else
    echo -e "${YELLOW}⚠️  docker-compose 파일을 찾을 수 없습니다.${NC}"
    echo "현재 디렉토리 파일 목록:"
    ls -la
fi

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

# Docker Compose 환경을 위한 DATABASE_URL 수정 (localhost -> postgres)
if [[ "$DATABASE_URL" == *"localhost"* ]]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL의 localhost를 postgres로 변경합니다 (Docker Compose 네트워크 환경)${NC}"
    DATABASE_URL_DOCKER="${DATABASE_URL//localhost/postgres}"
    # .env 파일도 업데이트
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL_DOCKER|g" "$ENV_FILE"
    export DATABASE_URL="$DATABASE_URL_DOCKER"
    echo -e "${GREEN}✅ DATABASE_URL 업데이트 완료: ${DATABASE_URL//:*:*/***}${NC}"
    
    # 실행 중인 컨테이너가 있으면 완전히 제거한 후 재생성하여 새로운 환경변수 적용
    if docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
        echo -e "${YELLOW}⚠️  실행 중인 app 컨테이너를 완전히 제거하고 재생성하여 새로운 DATABASE_URL을 적용합니다...${NC}"
        # docker-compose 명령어 대신 docker 명령어로 직접 제거 (ContainerConfig 오류 방지)
        docker stop adsp-quiz-backend 2>/dev/null || true
        docker rm -f adsp-quiz-backend 2>/dev/null || true
        # 컨테이너 이름으로 검색하여 모든 관련 컨테이너 제거
        docker ps -a --filter "name=adsp-quiz-backend" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
        # 컨테이너를 완전히 제거한 후 up 실행 (ContainerConfig 오류 방지)
        docker-compose --env-file "$ENV_FILE" up -d --no-deps app 2>&1 || {
            echo "컨테이너 시작 실패, 재시도..."
            sleep 2
            docker-compose --env-file "$ENV_FILE" up -d --no-deps app
        }
        sleep 5
    fi
fi

# 3. 데이터베이스 마이그레이션
echo -e "\n${YELLOW}[3/5] 데이터베이스 마이그레이션 실행${NC}"
# 프로젝트 디렉토리는 이미 시작 부분에서 이동했으므로 여기서는 이동 불필요

# PostgreSQL 컨테이너 상태 확인 및 시작
if ! docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-postgres.*Up"; then
    echo -e "${YELLOW}⚠️  PostgreSQL 컨테이너가 실행되지 않았습니다. 먼저 시작합니다...${NC}"
    docker-compose --env-file "$ENV_FILE" up -d postgres
    
    # PostgreSQL이 준비될 때까지 대기 (최대 30초)
    echo "PostgreSQL 컨테이너 준비 대기 중..."
    for i in {1..30}; do
        if docker-compose --env-file "$ENV_FILE" exec -T postgres pg_isready -U "${DB_USER}" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ PostgreSQL 준비 완료${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ PostgreSQL 준비 시간 초과${NC}"
            exit 1
        fi
        sleep 1
    done
fi

# app 컨테이너가 없으면 임시로 빌드 및 시작 (마이그레이션 실행용)
if ! docker-compose --env-file "$ENV_FILE" ps | grep -q "adsp-quiz-backend.*Up"; then
    echo -e "${YELLOW}⚠️  app 컨테이너가 없습니다. 마이그레이션을 위해 임시로 시작합니다...${NC}"
    
    # 기존 컨테이너가 있으면 완전히 제거 (ContainerConfig 오류 방지)
    if docker ps -a --format '{{.Names}}' | grep -q "^adsp-quiz-backend$"; then
        echo "기존 컨테이너 제거 중..."
        docker stop adsp-quiz-backend 2>/dev/null || true
        docker rm -f adsp-quiz-backend 2>/dev/null || true
    fi
    
    docker-compose --env-file "$ENV_FILE" build app
    
    # docker-compose up 대신 docker run을 사용하여 ContainerConfig 오류 방지
    # 또는 컨테이너를 완전히 제거한 후 up 실행
    docker-compose --env-file "$ENV_FILE" up -d --no-deps --force-recreate app 2>&1 || {
        # force-recreate가 실패하면 컨테이너를 직접 제거 후 재시도
        echo "컨테이너 재생성 실패, 직접 제거 후 재시도..."
        docker stop adsp-quiz-backend 2>/dev/null || true
        docker rm -f adsp-quiz-backend 2>/dev/null || true
        docker-compose --env-file "$ENV_FILE" up -d --no-deps app
    }
    
    # app 컨테이너가 준비될 때까지 대기 (최대 20초)
    echo "app 컨테이너 준비 대기 중..."
    sleep 5
fi

# 마이그레이션 실행 (환경변수를 직접 전달하여 DATABASE_URL 사용)
echo "마이그레이션 실행 중..."
if docker-compose --env-file "$ENV_FILE" exec -T -e DATABASE_URL="$DATABASE_URL" app alembic upgrade head; then
    echo -e "${GREEN}✅ 마이그레이션 완료${NC}"
else
    echo -e "${RED}❌ 마이그레이션 실패${NC}"
    echo "현재 DATABASE_URL: ${DATABASE_URL//:*:*/***}"
    echo "컨테이너 내부 환경변수 확인:"
    docker-compose --env-file "$ENV_FILE" exec -T app env | grep DATABASE_URL || echo "DATABASE_URL이 설정되지 않았습니다."
    exit 1
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
