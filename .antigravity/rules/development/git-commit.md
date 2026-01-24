# Git 커밋 규칙

## ⚠️ 절대 필수: 커밋 메시지 제안 전 체크리스트
**"커밋 준비해줘" 요청 시 반드시 다음 순서대로 수행 (순서 변경 금지):**
1. ✅ **이 규칙 파일 전체 읽기 완료** (`.antigravity/rules/development/git-commit.md`)
2. ✅ **현재 날짜 계산**: PowerShell `Get-Date -Format 'yyMMdd'` 실행
3. ✅ **형식 검증**: `yyMMdd > back-end > fast-api > 한 줄 설명` 형식 준수 확인
4. ✅ **금지 형식 검증**: `feat:`, `fix:`, `[FIX]` 등 Conventional Commits 형식 미사용 확인
5. ✅ **커밋 메시지 제안**: 위 모든 검증 통과 후에만 제안

**체크리스트 미수행 시 커밋 메시지 제안 금지**

## 기본 원칙
- **사용자 명시 요청 없이는 커밋/푸시 금지**
- `.gitignore` 확인 후 필요한 파일만 스테이징
- 커밋 시점의 날짜/시간, 한글 인코딩 반드시 확인
- **PowerShell 세션 시작 시 `chcp 65001` 필수 실행** (인코딩 규칙 참조)

## 커밋 요청 단계별 동작
- **"커밋 준비해줘"**
  - **1단계: 반드시 규칙 파일(`git-commit.md`) 전체 읽기 완료 확인** (절대 생략 금지)
  - **2단계: 현재 날짜 `yyMMdd` 형식 계산 (PowerShell: `Get-Date -Format 'yyMMdd'`)** (절대 생략 금지)
  - **3단계: 변경 사항 요약**
  - **4단계: 포함/제외 파일 제안**
  - **5단계: 커밋 메시지 초안 제안 (아래 절대 필수 형식만 사용)**
    - **절대 필수 형식**: `yyMMdd > back-end > fast-api > 한 줄 설명`
      - `yyMMdd`: 현재 날짜 (예: 260121)
      - `back-end`: 고정 문자열 (변경 금지)
      - `fast-api`: 고정 문자열 (변경 금지)
      - `한 줄 설명`: 변경 내용을 한 줄로 요약
    - **절대 금지**: 
      - `feat:`, `fix:`, `chore:`, `refactor:`, `docs:` 등 Conventional Commits 형식 사용 금지
      - `[FEAT]`, `[FIX]` 등 대괄호 형식 사용 금지
      - 날짜 형식 오류 (`20260121`, `26-01-21` 등)
      - `back-end` 대신 `backend`, `backend-api` 등 사용 금지
      - `fast-api` 대신 `fastapi`, `api` 등 사용 금지
    - **형식 검증 실패 시**: 제안하지 말고 규칙 재확인 후 다시 시도
  - **`git commit`, `git push` 실행 금지**
- **"커밋 및 푸시 진행해줘"**
  - 제안한 범위로 `git add` 수행
  - **커밋 메시지에 한글이 포함된 경우 반드시 별도 Python 스크립트 사용** (아래 "한글 커밋 메시지 작성" 참조)
  - 커밋 생성 후 **반드시 `git log -1 --pretty=format:"%s"`로 한글 깨짐 검증**
  - 검증 실패 시 즉시 `git commit --amend`로 수정 후 재검증
  - 사용자가 원하면 원격 브랜치로 `git push` 수행

## 커밋 메시지 형식 (절대 필수)
- **형식: `yyMMdd > back-end > fast-api > 한 줄 설명`**
- **구성 요소**:
  - `yyMMdd`: 6자리 날짜 (예: 260121 = 2026년 1월 21일)
  - `back-end`: 고정 문자열 (절대 변경 금지)
  - `fast-api`: 고정 문자열 (절대 변경 금지)
  - `한 줄 설명`: 변경 내용 요약 (50자 이내 권장)
- **커밋 메시지 제안 시 반드시 이 형식으로만 제안**
- **절대 금지 형식**:
  - ❌ `fix: AI 문제 생성 4지선다 형식으로 변경` (Conventional Commits)
  - ❌ `[FIX] AI 문제 생성 4지선다 형식으로 변경` (대괄호 형식)
  - ❌ `260121 > backend > fastapi > AI 문제 생성 4지선다 형식으로 변경` (고정 문자열 변경)
  - ❌ `20260121 > back-end > fast-api > AI 문제 생성 4지선다 형식으로 변경` (날짜 형식 오류)
- **올바른 예시**:
  - ✅ `260121 > back-end > fast-api > AI 문제 생성 4지선다 형식으로 변경`
  - ✅ `260120 > back-end > fast-api > 프로젝트 구조 리팩토링`
  - ✅ `260120 > back-end > fast-api > 폴더 구조 재구성 및 파일 크기 규칙 준수`
  - ✅ `260121 > back-end > fast-api > 프롬프트와 모델 스키마 4지선다 형식으로 수정`

## 한글 커밋 메시지 작성 (절대 필수)
- **한글이 포함된 커밋 메시지는 절대 `git commit -m "..."` 직접 사용 금지**
- **Windows 환경 주의**: PowerShell 등 터미널에서 문자열을 인자로 전달 시 인코딩이 깨질 수 있음
- 반드시 다음 절차 준수:
  1. **스크립트 방식**: `scripts/tools/git_commit_with_message.py` 사용 시 터미널 코드 페이지(`chcp 65001`)를 반드시 UTF-8로 변경 후 실행
  2. **바이트 방식 (권장)**: 인코딩 이슈가 지속될 경우, Python의 `write_bytes()`를 사용하여 직접 UTF-8 바이트를 파일에 쓰고 `git commit -F` 실행
  3. **검증 필수**: 커밋 후 `chcp 65001` 상태에서 `git log -1`을 실행하여 한글이 올바르게 표시되는지 육안으로 확인
  4. **재작업**: 깨진 문자 감지 시 즉시 `git commit --amend`로 수정
- 예시 스크립트 패턴:
  ```python
  # -*- coding: utf-8 -*-
  from pathlib import Path
  import subprocess
  commit_message = "260120 > back-end > fast-api > 한글 메시지"
  msg_file = Path("commit_msg.txt")
  msg_file.write_text(commit_message, encoding="utf-8", newline="\n")
  subprocess.run(["git", "commit", "-F", str(msg_file)])
  ```

## 금지 사항 (절대 위배 금지)
- 진행 로그/히스토리 나열식 커밋 본문 작성
- 사용자가 요청하지 않은 `git commit --amend`, 강제 푸시(`--force`)
- **한글 포함 커밋 메시지를 `git commit -m`으로 직접 전달**
- **PowerShell here-string 또는 Python 원라이너로 한글 커밋 메시지 작성**
- **커밋 메시지 형식 관련 (절대 금지)**:
  - ❌ `feat:`, `fix:`, `chore:`, `refactor:`, `docs:` 등 Conventional Commits 형식 사용
  - ❌ `[FEAT]`, `[FIX]` 등 대괄호 형식 사용
  - ❌ `back-end` 대신 `backend`, `backend-api` 등 사용
  - ❌ `fast-api` 대신 `fastapi`, `api` 등 사용
  - ❌ 날짜 형식 오류 (`20260121`, `26-01-21`, `2026-01-21` 등)
- **커밋 메시지 제안 관련 (절대 금지)**:
  - ❌ 규칙 파일(`git-commit.md`)을 읽지 않고 커밋 메시지 제안
  - ❌ 현재 날짜를 계산하지 않고 커밋 메시지 제안
  - ❌ 형식 검증 없이 커밋 메시지 제안
  - ❌ 프로젝트 규칙 형식(`yyMMdd > back-end > fast-api > ...`)을 확인하지 않고 커밋 메시지 제안
  - ❌ 체크리스트를 수행하지 않고 커밋 메시지 제안

## AI 작업 체크리스트 (커밋 메시지 제안 시 - 반드시 순서대로 수행)
1. ✅ **규칙 파일 읽기**: `.antigravity/rules/development/git-commit.md` 파일 읽기 완료
2. ✅ **문법 검증**: 수정된 Python 파일에 대해 `python -m py_compile` 실행 및 통과 확인 (Python 규칙 참조)
3. ✅ **날짜 계산**: PowerShell 명령어로 현재 날짜 `yyMMdd` 형식 계산 (`Get-Date -Format 'yyMMdd'`)
4. ✅ **형식 검증**: 제안할 메시지가 `yyMMdd > back-end > fast-api > 한 줄 설명` 형식인지 확인
5. ✅ **금지 형식 검증**: 
   - `feat:`, `fix:`, `chore:` 등 Conventional Commits 형식 미사용 확인
   - `[FEAT]`, `[FIX]` 등 대괄호 형식 미사용 확인
   - `back-end` 대신 다른 문자열 사용하지 않았는지 확인
   - `fast-api` 대신 다른 문자열 사용하지 않았는지 확인
   - 날짜 형식이 정확히 `yyMMdd`인지 확인
5. ✅ **최종 검증**: 제안할 메시지를 다시 한 번 확인하고 규칙 준수 여부 검증
6. ✅ **커밋 메시지 제안**: 위 모든 검증 통과 후에만 메시지 제안

**중요**: 체크리스트 중 하나라도 실패하면 메시지를 제안하지 말고 규칙을 재확인하라.
