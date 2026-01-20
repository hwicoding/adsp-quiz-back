#!/bin/bash
# 최근 커밋 메시지를 프로젝트 규칙(yyMMdd > back-end > fast-api > ...)에 맞게 수정하는 스크립트
# git rebase --exec 와 함께 사용.

set -e

CURRENT_MSG="$(git log -1 --pretty=%s)"

case "$CURRENT_MSG" in
  "260120 > back-end > scripts > 폴더 구조 재구성 및 파일 크기 규칙 준수")
    NEW_MSG="260120 > back-end > fast-api > 폴더 구조 재구성 및 파일 크기 규칙 준수"
    ;;

  "260119 > back-end > deploy > build-app.sh 컨테이너 상태 확인 로직 개선")
    NEW_MSG="260119 > back-end > fast-api > build-app.sh 컨테이너 상태 확인 로직 개선"
    ;;

  "260119 > back-end > deploy > 컨테이너 재시작 상태 감지 및 대기 로직 추가")
    NEW_MSG="260119 > back-end > fast-api > 컨테이너 재시작 상태 감지 및 대기 로직 추가"
    ;;

  *)
    # 수정 대상이 아니면 그대로 통과
    exit 0
    ;;
esac

git commit --amend -m "$NEW_MSG"

