# CI/CD 배포 규칙

## 배포 전 체크리스트 (필수)
- 문법 검증: 모든 Python 파일 `python -m py_compile` 통과 확인 (SyntaxError 방지)
- 환경변수 확인: `DATABASE_URL`, `GEMINI_API_KEY`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `ENVIRONMENT`, `PORT`
- 환경변수 파일 권한 확인: `chmod 600 env/.env`
- 마이그레이션 스크립트 검증
- 의존성 업데이트 확인 (`pyproject.toml`)
- 테스트 통과 확인
- SSH 키 쌍 확인: GitHub Secrets의 `SSH_PRIVATE_KEY`와 서버 공개 키 일치 확인
- 서버 접근성 확인: SSH 서비스 상태, 포트, 방화벽, 네트워크 연결 확인

## 배포 중 절차 (필수)
- 기존 서비스 중지: `docker-compose down`
- 데이터베이스 백업: `docker exec adsp-quiz-postgres pg_dump -U adsp_quiz_user adsp_quiz_db > backup_$(date +%Y%m%d_%H%M%S).sql`
- 새 버전 배포: `docker-compose build --no-cache && docker-compose up -d`
- **마이그레이션 실행 필수**: `build-app.sh` 또는 `deploy.sh` 사용 시 자동 실행, 수동 배포 시 `docker-compose exec app alembic upgrade head` 필수
- **초기 데이터 검증**: `scripts/db/verify-initial-data.sh` 실행 (주요항목 8개, 세부항목 28개 확인)
- 헬스 체크 확인: `curl https://adsp-api.livbee.co.kr/health`

## 배포 후 확인 (필수)
- API 동작 확인 (루트, 헬스체크, 주요 엔드포인트)
- 데이터베이스 연결 확인
- 초기 데이터 존재 확인 (main_topics 8개, sub_topics 28개, 특히 sub_topic_id=1,2 존재)
- 로그 모니터링: `docker logs adsp-quiz-backend`

## GitHub Actions 배포
- `main` 브랜치 푸시 시 자동 배포 (`.github/workflows/deploy.yml`)
- GitHub Secrets 필수 항목: `SERVER_HOST`, `SERVER_USER`, `SSH_PRIVATE_KEY`, `SERVER_PORT`, `DATABASE_URL`, `DB_USER`, `DB_PASSWORD`, `GEMINI_API_KEY`, `SECRET_KEY`, `ALLOWED_ORIGINS`
- SSH 키 쌍 확인 필수: 배포 전 반드시 확인

## 워크플로우 작성 규칙 (필수)
- 워크플로우 파일 최소화: 복잡한 로직은 별도 스크립트로 분리
- 스크립트 분리 기준: 10줄 이상의 복잡한 로직은 반드시 별도 스크립트로 분리
- 스크립트 폴더 구조: `scripts/deploy/`, `scripts/env/`, `scripts/db/`, `scripts/utils/`
- 스크립트 실행: 존재 여부 확인 후 실행, 실행 권한 설정 필수

## ContainerConfig 오류 해결 (필수)
- `docker-compose down` 실행 후 모든 관련 컨테이너 완전 제거
- 컨테이너 제거 후 `docker-compose build --no-cache && docker-compose up -d` 실행
- 절대 금지: `docker-compose stop`만 하고 `docker-compose down` 없이 컨테이너 제거 시도
