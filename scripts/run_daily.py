from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config, path_from_config
from src.dedupe import filter_duplicates
from src.email_sender import can_send_email, send_email
from src.scoring import score_items
from src.search import search_all
from src.storage import Store
from src.summarize import daily_subject, render_daily_report, write_report
from src.text_utils import short_hash
from src.zotero_client import ZoteroClient


def main() -> int:
    config = load_config()
    store = Store(path_from_config(config, "database"))
    try:
        today = date.today().isoformat()
        if store.has_recommendation_for_date(today):
            print(f"Daily recommendation already exists for {today}; skipping duplicate send.")
            return 0

        zotero = ZoteroClient()
        zotero_items = zotero.existing_items() if zotero.configured else []
        candidates = search_all(config)
        candidates = filter_duplicates(candidates, store.seen_keys(), zotero_items)
        ranked = score_items(candidates)
        if not ranked:
            print("No new literature candidates found after dedupe.")
            return 2

        item = ranked[0]
        item.candidate_id = f"{today}_{short_hash(item.doi or item.title)}"
        store.save_candidate(item)
        store.save_recommendation(item)

        body = render_daily_report(item)
        filename = f"{today}.md"
        path = write_report(body, path_from_config(config, "daily_reports"), filename)
        print(f"Daily report written: {path}")

        if can_send_email():
            send_email(daily_subject(item), body)
            print("Daily email sent.")
        else:
            print("Email not sent: MAIL_FROM and GMAIL_APP_PASSWORD are not fully configured.")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
