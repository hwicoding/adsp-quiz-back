#!/bin/bash
# BOM 제거 스크립트
# 사용법: ./scripts/remove-bom.sh [파일경로]

set -e

ENV_FILE="${1:-${ENV_FILE:-/opt/adsp-quiz-backend/env/.env}}"

if [ ! -f "$ENV_FILE" ]; then
    exit 0
fi

# Python으로 BOM 제거
if command -v python3 &> /dev/null; then
    python3 -c "
import sys
with open('$ENV_FILE', 'rb') as f:
    content = f.read()
if content.startswith(b'\xef\xbb\xbf'):
    with open('$ENV_FILE', 'wb') as f:
        f.write(content[3:])
" 2>/dev/null || true
else
    sed -i '1s/^\xEF\xBB\xBF//' "$ENV_FILE" 2>/dev/null || true
fi
