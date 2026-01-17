#!/bin/bash
# 컨테이너 제거 스크립트
# 사용법: ./scripts/remove-containers.sh [컨테이너이름패턴]

set -e

CONTAINER_PATTERN="${1:-adsp-quiz-backend}"

docker ps -a --filter "name=$CONTAINER_PATTERN" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

for container_id in $(docker ps -a --format "{{.ID}}" --filter "name=$CONTAINER_PATTERN"); do
    docker rm -f "$container_id" 2>/dev/null || true
done
