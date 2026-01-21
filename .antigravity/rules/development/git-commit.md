# Git 커밋 규칙

## 기본 원칙
- **사용자 명시 요청 없이는 커밋/푸시 금지**
- `.gitignore` 확인 후 필요한 파일만 스테이징
- 커밋 시점의 날짜/시간, 한글 인코딩 반드시 확인
- **PowerShell 세션 시작 시 `chcp 65001` 필수 실행** (인코딩 규칙 참조)

## 커밋 요청 단계별 동작
- **"커밋 준비해줘"**
  - 변경 사항 요약
  - 포함/제외 파일 제안
  - **커밋 메시지 초안 제안 (반드시 아래 형식 준수)**
    - 형식: `yyMMdd > back-end > fast-api > 한 줄 설명`
    - 현재 날짜 기준 `yyMMdd` 계산 필수
    - 형식이 맞지 않으면 제안하지 말고 규칙 재확인
  - **`git commit`, `git push` 실행 금지**
- **"커밋 및 푸시 진행해줘"**
  - 제안한 범위로 `git add` 수행
  - **커밋 메시지에 한글이 포함된 경우 반드시 별도 Python 스크립트 사용** (아래 "한글 커밋 메시지 작성" 참조)
  - 커밋 생성 후 **반드시 `git log -1 --pretty=format:"%s"`로 한글 깨짐 검증**
  - 검증 실패 시 즉시 `git commit --amend`로 수정 후 재검증
  - 사용자가 원하면 원격 브랜치로 `git push` 수행

## 커밋 메시지 형식 (절대 필수)
- **형식: `yyMMdd > back-end > fast-api > 한 줄 설명`**
- `back-end`, `fast-api`는 **고정**
- **커밋 메시지 제안 시 반드시 이 형식으로만 제안**
- `feat:`, `fix:`, `chore:` 등 Conventional Commits 형식 사용 금지
- 예시:
  - `260120 > back-end > fast-api > 프로젝트 구조 리팩토링`
  - `260120 > back-end > fast-api > 폴더 구조 재구성 및 파일 크기 규칙 준수`

## 한글 커밋 메시지 작성 (절대 필수)
- **한글이 포함된 커밋 메시지는 절대 `git commit -m "..."` 직접 사용 금지**
- 반드시 다음 절차 준수:
  1. **우선 `scripts/tools/git_commit_with_message.py` 스크립트 사용** (권장)
     - 사용법: `python scripts/tools/git_commit_with_message.py "커밋 메시지"`
     - 스크립트가 자동으로 UTF-8 파일 생성 및 `git commit -F` 실행
  2. 스크립트 사용 불가 시 별도 Python 스크립트 파일 생성 (`# -*- coding: utf-8 -*-` 헤더 필수)
  3. 커밋 메시지를 UTF-8로 파일에 저장 (`open(..., encoding='utf-8', newline='\n')`)
  4. `git commit -F <파일경로>` 또는 `git commit --amend -F <파일경로>` 사용
  5. 스크립트 및 임시 파일은 커밋 후 즉시 삭제
  6. **커밋 후 반드시 `git log -1 --pretty=format:"%s"`로 한글 정상 표시 확인**
  7. 깨진 문자(諛, 異, ?? 등) 감지 시 즉시 `git commit --amend -F <파일경로>`로 재작업
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

## 금지 사항
- 진행 로그/히스토리 나열식 커밋 본문 작성
- 사용자가 요청하지 않은 `git commit --amend`, 강제 푸시(`--force`)
- **한글 포함 커밋 메시지를 `git commit -m`으로 직접 전달**
- **PowerShell here-string 또는 Python 원라이너로 한글 커밋 메시지 작성**
- **`feat:`, `fix:`, `chore:` 등 Conventional Commits 형식 사용**
- **프로젝트 규칙 형식(`yyMMdd > back-end > fast-api > ...`)을 확인하지 않고 커밋 메시지 제안**
