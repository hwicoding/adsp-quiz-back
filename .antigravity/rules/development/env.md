# 환경변수 관리 규칙

## 기본 규칙
- `.env` 파일 사용 (Git 제외 필수)
- Pydantic Settings 사용 (`pydantic-settings` 패키지의 `BaseSettings`)
- `.env` 파일은 반드시 UTF-8 인코딩(BOM 없음)으로 저장

## BOM 제거 규칙 (필수)
- `.env` 파일을 `source` 명령어로 읽을 때 BOM이 있으면 첫 번째 줄의 주석이 명령어로 해석되어 오류 발생
- 배포 스크립트에서 `.env` 파일을 읽기 전에 반드시 BOM 제거 필수
- BOM 제거 방법: Python 스크립트 사용 (권장)

## 파일 작성 방법 (절대 필수)
- PowerShell here-string 사용 절대 금지
- Python 원라이너(`python -c`) 사용 절대 금지
- 반드시 별도 Python 스크립트 파일 사용
- 스크립트 헤더에 `# -*- coding: utf-8 -*-` 명시
- `open(file, 'w', encoding='utf-8', newline='\n')` 사용
- 파일 수정 시 기존 파일 읽기 → 수정 → 저장 방식 사용

## 환경변수 검증 (절대 필수)
- 환경변수 업데이트 후 반드시 검증 필수
- DATABASE_URL 형식 검증: `^postgresql(\+asyncpg)?://[^@]+@` 패턴으로 사용자명과 비밀번호 포함 여부 확인
- 필수 환경변수 값 검증: `DB_USER`, `DB_PASSWORD`, `DATABASE_URL`이 비어있지 않은지 확인
- 데이터베이스 비밀번호 검증: PostgreSQL 컨테이너의 실제 비밀번호와 `.env` 파일의 비밀번호 일치 확인
- 검증 실패 시 배포 중단 (`exit 1`)

## 필수 환경변수
- `DATABASE_URL`: 데이터베이스 연결 정보
- `GEMINI_API_KEY`: Gemini API 키
- `SECRET_KEY`: 강력한 랜덤 문자열 (최소 32자)
- `ALLOWED_ORIGINS`: 프론트엔드 도메인 (콤마로 구분)

## Docker Compose 환경변수 규칙
- `env_file`로 `.env`를 읽을 때는 `environment`에서 `KEY=${KEY}` 형태 사용 금지 (호스트 환경변수/루트 `.env`에 값이 없으면 빈 문자열로 덮어씀)
- 이 조합이 필요하면 `environment`에는 `KEY`만 나열해서 `env_file` 값이 그대로 전달되도록 할 것
- `.env` 파일 업데이트 후 실행 중인 컨테이너가 있으면 재시작하여 새 환경변수 적용 필수

## GitHub Actions 배포 시 환경변수 전달 규칙
- GitHub Actions Secrets의 환경변수는 SSH 세션으로 직접 전달해야 함
- `ssh ... 'bash -s' < script.sh` 형태는 로컬 환경변수를 자동으로 전달하지 않음
- 환경변수 전달 방법: `ssh ... "VAR1='${VAR1}' VAR2='${VAR2}' bash -s" < script.sh`
- heredoc 중첩 사용 금지 (스크립트 내부 heredoc과 충돌 가능)

## DATABASE_URL 호스트명 변환 규칙 (절대 필수)
- GitHub Actions Secrets의 `DATABASE_URL`이 `localhost` 또는 `127.0.0.1`을 사용할 수 있음
- Docker Compose 네트워크에서는 컨테이너 간 통신을 위해 서비스 이름(`postgres`)을 사용해야 함
- 배포 스크립트에서 `.env` 파일 생성 전에 반드시 `localhost`/`127.0.0.1`을 `postgres`로 자동 변환
- 변환 로직: `sed 's/@localhost/@postgres/g' | sed 's/@127\.0\.0\.1/@postgres/g'`

## 마이그레이션 스크립트 환경변수 사용 규칙
- `docker-compose exec`로 마이그레이션 실행 시 `-e DATABASE_URL="$DATABASE_URL"` 형태 사용 금지
- 호스트의 환경변수가 비어있거나 잘못된 값일 수 있음
- 컨테이너 내부에서는 이미 `env_file: - ./env/.env`로 환경변수가 설정되어 있음
- 마이그레이션 실행: `docker-compose --env-file "$ENV_FILE" exec -T app alembic upgrade head`
- 컨테이너 내부 환경변수를 그대로 사용하도록 할 것

## 민감 정보 관리 (절대 필수)
- `.env` 파일은 절대 Git에 커밋하지 않음 (`.gitignore` 확인 필수)
- 서버 담당자로부터 받은 `.env` 내용은 별도 스크립트로 생성 (`scripts/setup/create-env-file.py`)
- 로컬 테스트 시 `DATABASE_URL` 호스트명 변경 필요 (서버: `postgres`, 로컬: `localhost`)
- `.env` 파일 생성 후 반드시 DB 연결 테스트 수행 (`scripts/test/test-db-query.py`)
- 민감 정보가 포함된 문서는 `docs/` 폴더에 저장 시 주의 (필요시 마스킹)
