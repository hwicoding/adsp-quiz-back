# -*- coding: utf-8 -*-
"""
한글 커밋 메시지 안전 적용 스크립트.

사용 예시:
  python scripts/tools/git_commit_with_message.py "260121 > back-end > fast-api > 설명"
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: python scripts/tools/git_commit_with_message.py \"커밋 메시지\"")
        return 1

    commit_message = sys.argv[1]

    repo_root = Path(__file__).resolve().parents[2]
    msg_file = repo_root / ".git" / "COMMIT_MESSAGE.txt"

    msg_file.write_text(commit_message, encoding="utf-8", newline="\n")

    try:
        subprocess.run(
            ["git", "commit", "-F", str(msg_file)],
            cwd=str(repo_root),
            check=True,
        )
        return 0
    finally:
        try:
            msg_file.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

