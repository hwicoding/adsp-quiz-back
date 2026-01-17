#!/bin/bash
# Git 코드 동기화 스크립트
# 사용법: ./scripts/git-sync.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-/opt/adsp-quiz-backend}"

cd "$PROJECT_DIR" || exit 1

echo "최신 코드 가져오기..."
git fetch origin
git reset --hard origin/main
git clean -fd --exclude='data/postgres' || true

echo "✅ 코드 동기화 완료"
