from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config, path_from_config
from src.email_sender import can_send_email, send_email
from src.storage import Store
from src.summarize import render_weekly_report, weekly_subject, write_report


def main() -> int:
    config = load_config()
    store = Store(path_from_config(config, "database"))
    try:
        items = store.recent_recommendations(limit=7)
        body = render_weekly_report(items)
        year, week, _ = date.today().isocalendar()
        filename = f"{year}-week-{week:02d}.md"
        path = write_report(body, path_from_config(config, "weekly_reports"), filename)
        print(f"Weekly report written: {path}")
        if can_send_email():
            send_email(weekly_subject(), body)
            print("Weekly email sent.")
        else:
            print("Email not sent: MAIL_FROM and GMAIL_APP_PASSWORD are not fully configured.")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())

