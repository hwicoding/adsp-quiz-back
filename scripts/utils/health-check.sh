#!/bin/bash
# 헬스체크 스크립트
# 사용법: ./scripts/health-check.sh [URL] [최대재시도] [재시도간격] [ENV_FILE]

set -e

HEALTH_CHECK_URL="${1:-https://adsp-api.livbee.co.kr/health}"
MAX_RETRIES="${2:-5}"
RETRY_DELAY="${3:-10}"
ENV_FILE="${4:-${ENV_FILE:-/opt/adsp-quiz-backend/env/.env}}"

for i in $(seq 1 $MAX_RETRIES); do
    echo "헬스체크 시도 $i/$MAX_RETRIES..."
    sleep $RETRY_DELAY
    
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" || echo "000")
    echo "헬스체크 응답: HTTP $HEALTH_RESPONSE"
    
    if [ "$HEALTH_RESPONSE" = "200" ]; then
        echo "✅ 배포 성공! 헬스체크 통과 (HTTP $HEALTH_RESPONSE)"
        exit 0
    else
        if [ $i -eq $MAX_RETRIES ]; then
            echo "❌ 헬스체크 실패 (최대 재시도 횟수 도달)"
            echo "최종 응답 코드: HTTP $HEALTH_RESPONSE"
            if [ -f "$ENV_FILE" ]; then
                echo "애플리케이션 로그:"
                docker-compose --env-file "$ENV_FILE" logs app | tail -50 || true
                echo "컨테이너 상태:"
                docker-compose --env-file "$ENV_FILE" ps || true
            fi
            exit 1
        else
            echo "⚠️  헬스체크 실패 (HTTP $HEALTH_RESPONSE), 재시도 중..."
        fi
    fi
done
