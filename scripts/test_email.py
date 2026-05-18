from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.email_sender import send_email


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Build the email without sending it.")
    args = parser.parse_args()
    msg = send_email(
        "[ASD文献推荐系统] Gmail测试成功",
        "如果你收到这封邮件，说明每日文献推荐系统的 Gmail 发送功能已经配置成功。",
        dry_run=args.dry_run,
    )
    print(f"Email prepared for {msg['To']}. dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

