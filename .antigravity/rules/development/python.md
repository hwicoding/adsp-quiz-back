# Python 개발 규칙

## 기본 원칙
- **비동기 필수**: 모든 I/O 작업(DB, 외부 API)은 `async`/`await` 필수 사용
- **타이핑**: Pydantic 모델 및 Type Hinting 적극 활용
- **문법 검증**: 작업 완료 후 반드시 문법 검증 실행

## 문법 검증 (절대 필수)
- **커밋 전/배포 전 반드시 실행**:
  - `python -m py_compile [수정된_파일_경로]`
  - 또는 전체 검증: `Get-ChildItem -Recurse -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }`
- **목적**: `SyntaxError`로 인한 컨테이너 시작 실패 및 배포 중단 방지

## 코드 스타일
- **SOLID 원칙**: 단일 책임 원칙 준수 (Service 레이어 비대화 방지)
- **로깅**: `logger.info`, `logger.error` 등을 사용하여 주요 흐름 기록
- **에러 처리**: `try...except` 블록 사용 시 인덴트 주의 및 구체적인 예외 처리

## 주요 라이브러리 활용
- **FastAPI**: 의존성 주입(`Depends`) 활용, 스키마 분리
- **SQLAlchemy**: 비동기 세션 활용, Eager Loading 설정
- **Pydantic Settings**: 환경변수 관리 및 검증
