# 프로젝트 규칙

## 핵심 원칙
**1순위: 채팅 토큰 최대 절약**

## 기본 규칙
- **응답**: 간결하고 핵심만, 불필요한 설명/예시/중복 최소화
- **코드**: 필요한 코드만, 주석 최소화, 명확한 변수명으로 자명한 코드
- **대화**: 명확하고 구체적인 질문, 한 번에 하나의 작업, 확인 질문 최소화
- **파일/도구**: 필요한 파일만 읽기, 불필요한 검색 최소화, 병렬 처리
- **터미널**: PowerShell 세션 시작 시 `chcp 65001` 필수, 한글 출력 전 재확인

## 필수 규칙 (상세는 `rules/` 참조)
- **SOLID 원칙**: 컴포넌트/함수/클래스는 단일 책임, 확장 가능하도록 설계, 작업 완료 전 검증 필수
- **한글 인코딩**: UTF-8 사용, PowerShell here-string/Python 원라이너 한글 사용 금지 → [상세](./rules/development/encoding.md)
- **docs 폴더**: 파일명 영문, 내용 한글, 50줄 이내, 로그 형태 금지, 중복 제거, 폴더화 필수 → [상세](./rules/management/docs.md)
- **규칙 파일**: 50줄 이내, 5개 이상 시 폴더화, 도메인별 분리 → [상세](./rules/management/rules.md)
- **프로젝트 구조**: FastAPI 레이어 분리 (API→Service→CRUD→Model), 도메인별 모듈화, 비동기 필수 → [상세](./rules/development/structure.md)
- **scripts/워크플로우**: 스크립트/워크플로우 파일은 50줄 이내, 폴더당 5개 이하, 도메인별 폴더화 → [상세](./rules/structure/scripts.md)
- **환경변수**: `.env` UTF-8(BOM 없음), Pydantic Settings, 업데이트 후 검증 필수 → [상세](./rules/development/env.md)
- **Docker**: 멀티 스테이지 빌드, `migrations/` 절대 제외 금지 → [상세](./rules/development/docker.md)
- **마이그레이션**: Alembic 사용, 배포 시 자동 실행, 실패 시 배포 중단 → [상세](./rules/database/migration.md)
- **Python**: 비동기 필수, **문법 검증(`py_compile`) 필수**, SOLID 준수 → [상세](./rules/development/python.md)
- **SQLAlchemy**: 비동기 컨텍스트에서 lazy loading 금지, 관계 접근 시 eager loading 필수 → [상세](./rules/database/sqlalchemy.md)
- **프론트엔드**: 배포 상태 확인 최우선, 배포 후 검증, 응답 문서 작성 → [상세](./rules/integration/frontend.md)
- **배포**: 환경변수/마이그레이션/의존성/테스트/SSH 키 확인 필수 → [상세](./rules/deployment/ci-cd.md)
- **의존성**: `pyproject.toml` 사용, 외부 라이브러리 API 변경 대응 → [상세](./rules/development/dependencies.md)
- **Git 커밋**: 명시적 요청 없이 커밋/푸시 금지, 단계별 동작(`커밋 준비해줘`=제안, `커밋 및 푸시 진행해줘`=실행), **커밋 메시지 제안 전 반드시 규칙 파일 전체 읽기 및 체크리스트 수행 필수**, 날짜/인코딩 검증, 형식 `yyMMdd > back-end > fast-api > 한 줄 설명` 절대 준수 → [상세](./rules/development/git-commit.md)
- **테스트**: pytest + pytest-asyncio, 새 API 엔드포인트 테스트 필수, 외부 API 모킹, 커버리지 80% 이상 목표
- **에러 응답**: `code`와 `detail` 필드 구조화, 환경별 메시지 차별화, 상세 로깅 필수 → [상세](./rules/development/error-response.md)
- **AI 서비스**: 프롬프트와 모델 스키마 일관성 검증 필수, 제약 조건 일치 확인 → [상세](./rules/development/ai-service.md)
- **문제 생성 캐싱**: 적정선 기준(30개) 준수, 유사도 체크(토큰 없이), 캐시 문제 변형 적용(70% 확률), 토큰 절약 최우선
- **유사도 계산**: 한국어 특성 고려 (조사/어미 제거, 유사 표현 정규화, n-gram 조합), 토큰 없이 정교한 계산 필수
- **문제 생산 제어**: 재시도 초과 시 생산 중단, 핵심 정보 변경 시에만 재시도, 대시보드에서 카테고리별 상태 표시 필수
- **작업 효율화**: 프로젝트 계획 Phase 순서 준수, 하위 레이어→상위 레이어 순서, 독립 작업 병렬 처리
