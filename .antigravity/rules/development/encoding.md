# 한글 인코딩 규칙

## 핵심 규칙
- 모든 파일은 UTF-8 인코딩 사용 (BOM 없음)
- PowerShell here-string(`@'...'@`) 사용 절대 금지
- Python 원라이너(`python -c`)에서 한글 문자열 사용 절대 금지
- 한글 포함 파일 수정 시 반드시 별도 Python 스크립트 파일 사용
- 파일 저장 후 반드시 검증 (별도 Python 검증 스크립트 사용)

## 터미널 인코딩 (필수)
- PowerShell 세션 시작 시 첫 명령어로 `chcp 65001` 실행 필수
- 파일 읽기/쓰기 명령어 실행 전 반드시 `chcp 65001` 확인
- 한글 출력 예상 명령어 실행 전 인코딩 재확인
- **`git commit` 실행 전 반드시 `chcp 65001` 확인 및 한글 커밋 메시지 검증 절차 준수**

## 파일 작성 방법 (절대 필수)
- `.env` 파일 등 한글 포함 파일 작성 시:
  1. PowerShell here-string 사용 절대 금지
  2. Python 원라이너 사용 절대 금지
  3. 반드시 별도 `.py` 스크립트 파일 사용
  4. 스크립트 헤더에 `# -*- coding: utf-8 -*-` 명시
  5. `open(file, 'w', encoding='utf-8', newline='\n')` 사용
  6. 파일 수정 시 기존 파일 읽기 → 수정 → 저장 방식 사용

## Git 커밋 메시지 인코딩 (절대 필수)
- **한글이 포함된 커밋 메시지는 절대 PowerShell에서 직접 전달 금지**
- **Windows 인자 전달 이슈**: 터미널 인자로 한글 전달 시 `chcp 65001` 상태라도 깨질 수 있음
- **안전한 방법**: 
  1. Python `write_bytes()`를 사용하여 UTF-8 바이트를 파일에 직접 쓰기
  2. `git commit -F [파일경로]` 명령어로 커밋 수행
- 커밋 후 즉시 `chcp 65001` 상태에서 `git log -1`로 육안 검증
- 깨진 문자 감지 시 즉시 `git commit --amend`로 수정
- 상세 규칙은 `rules/development/git-commit.md` 참조

## 검증 (필수)
- 파일 저장 후 별도 Python 검증 스크립트로 한글 확인
- 깨진 문자(諛, 異, ?? 등) 감지 시 즉시 재작업
- `Get-Content -Encoding UTF8`로 확인하여 한글 정상 표시 확인
- **커밋 메시지 한글 검증은 `git log -1 --pretty=format:"%s"`로 반드시 확인**
