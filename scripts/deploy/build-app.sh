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
if [ -f "${PROJECT_DIR}/scripts/utils/remove-containers.sh" ]; then
    chmod +x "${PROJECT_DIR}/scripts/utils/remove-containers.sh"
    "${PROJECT_DIR}/scripts/utils/remove-containers.sh" "adsp-quiz-backend"
    "${PROJECT_DIR}/scripts/utils/remove-containers.sh" "adsp-quiz-postgres"
fi

# 네트워크 정리 (선택적)
docker network prune -f 2>/dev/null || true

echo "Docker 이미지 빌드 중..."
# 캐시 사용하여 빌드 (첫 빌드가 아니면 캐시 활용)
docker-compose --env-file "$ENV_FILE" build

echo "애플리케이션 컨테이너 시작 중..."
docker-compose --env-file "$ENV_FILE" up -d

echo "컨테이너 시작 대기 중..."
sleep 3

# 컨테이너가 안정적으로 실행 중인지 확인 (재시작 중이 아닌지)
MAX_WAIT=30
WAIT_COUNT=0
CONTAINER_ID=""

# 컨테이너 ID 가져오기
while [ -z "$CONTAINER_ID" ] && [ $WAIT_COUNT -lt 5 ]; do
    CONTAINER_ID=$(docker-compose --env-file "$ENV_FILE" ps -q app 2>/dev/null || echo "")
    if [ -z "$CONTAINER_ID" ]; then
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
    fi
done

if [ -z "$CONTAINER_ID" ]; then
    echo "❌ 컨테이너 ID를 찾을 수 없습니다"
    docker-compose --env-file "$ENV_FILE" ps
    exit 1
fi

WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # docker inspect로 직접 상태 확인
    CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER_ID" 2>/dev/null || echo "")
    IS_RESTARTING=$(docker inspect --format='{{.State.Restarting}}' "$CONTAINER_ID" 2>/dev/null || echo "false")
    
    if [ "$CONTAINER_STATUS" = "running" ] && [ "$IS_RESTARTING" = "false" ]; then
        # 헬스체크 확인 (가능한 경우)
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_ID" 2>/dev/null || echo "")
        if [ -z "$HEALTH_STATUS" ] || [ "$HEALTH_STATUS" = "healthy" ] || [ "$HEALTH_STATUS" = "" ]; then
            echo "✅ 애플리케이션 컨테이너 실행 중"
            break
        else
            echo "컨테이너 헬스체크 대기 중... ($WAIT_COUNT/$MAX_WAIT)"
            sleep 2
            WAIT_COUNT=$((WAIT_COUNT + 2))
        fi
    elif [ "$IS_RESTARTING" = "true" ]; then
        echo "⚠️  컨테이너가 재시작 중입니다. 대기 중... ($WAIT_COUNT/$MAX_WAIT)"
        sleep 2
        WAIT_COUNT=$((WAIT_COUNT + 2))
    else
        echo "컨테이너 상태: $CONTAINER_STATUS, 대기 중... ($WAIT_COUNT/$MAX_WAIT)"
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
    fi
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "❌ 애플리케이션 컨테이너 시작 실패 (타임아웃)"
    echo "컨테이너 상태:"
    docker-compose --env-file "$ENV_FILE" ps app
    echo ""
    echo "컨테이너 상세 정보:"
    docker inspect --format='Status: {{.State.Status}}, Restarting: {{.State.Restarting}}, Health: {{.State.Health.Status}}' "$CONTAINER_ID" 2>/dev/null || echo "컨테이너 정보를 가져올 수 없습니다"
    echo ""
    echo "컨테이너 로그:"
    docker-compose --env-file "$ENV_FILE" logs --tail=50 app
    exit 1
fi
