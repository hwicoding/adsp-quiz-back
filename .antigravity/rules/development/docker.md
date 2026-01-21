# Docker 규칙

## 기본 규칙
- 멀티 스테이지 빌드 사용
- Docker Compose로 개발/배포 환경 일관성 유지
- 환경변수 주입: Docker Compose에서 `.env` 파일 자동 로드
- 헬스 체크: 서비스 간 의존성 관리 (`depends_on` + `condition: service_healthy`)

## .dockerignore 규칙 (절대 필수)
- 불필요한 파일 제외 (`.git`, `docs/`, `.env` 등)
- **⚠️ 중요: migrations 디렉토리는 절대 제외하지 않음**
- `.dockerignore`에 `migrations/` 또는 `migrations/**` 패턴이 있으면 제거 필수

## Dockerfile 마이그레이션 파일 복사 (절대 필수)
- Dockerfile에서 `migrations/` 디렉토리를 반드시 복사해야 함
- `COPY migrations/ /app/migrations/` 명령어 필수 포함
- `COPY alembic.ini /app/` 명령어 필수 포함
- 빌드 후 컨테이너 내부에 `/app/migrations/versions/` 디렉토리 및 파일이 존재하는지 확인 필수

## ContainerConfig 오류 해결 (절대 필수)
- `docker-compose down` 실행 후 모든 관련 컨테이너를 docker 명령어로 직접 제거
- 컨테이너 제거 후 `docker-compose build --no-cache && docker-compose up -d` 실행
- 절대 금지: `docker-compose stop`만 하고 `docker-compose down` 없이 컨테이너 제거 시도

## 마이그레이션 실행 규칙 (절대 필수)
- 마이그레이션 실행 시 `docker-compose exec -e DATABASE_URL="$DATABASE_URL"` 형태 사용 금지
- 호스트의 환경변수가 비어있거나 잘못된 값일 수 있음
- 컨테이너 내부에서는 이미 `env_file: - ./env/.env`로 환경변수가 설정되어 있음
- 올바른 실행 방법: `docker-compose --env-file "$ENV_FILE" exec -T app alembic upgrade head`
- `.env` 파일 업데이트 후 컨테이너 재시작하여 새 환경변수 적용 필수
