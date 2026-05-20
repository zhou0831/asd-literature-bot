from __future__ import annotations

import sys
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config, path_from_config
from src.dedupe import filter_duplicates
from src.email_sender import can_send_email, send_email
from src.scoring import is_recommendable, score_items
from src.search import search_all
from src.storage import Store
from src.summarize import daily_subject, render_daily_report, write_report
from src.text_utils import short_hash
from src.zotero_client import ZoteroClient


def select_daily_item(ranked):
    if not ranked:
        return None, "none"
    item = next((candidate for candidate in ranked if is_recommendable(candidate)), None)
    if item is not None:
        item.recommendation_tier = "core"
        item.low_confidence = False
        return item, "core"
    item = next((candidate for candidate in ranked if not candidate.strong_exclusion), None)
    if item is not None:
        item.recommendation_tier = "exploratory" if item.topic_fit_score >= 35 or item.recommendation_score >= 45 else "background"
        item.low_confidence = True
        return item, item.recommendation_tier
    item = ranked[0]
    item.recommendation_tier = "very_low_confidence"
    item.low_confidence = True
    return item, "very_low_confidence"


def main() -> int:
    config = load_config()
    store = Store(path_from_config(config, "database"))
    try:
        today = date.today().isoformat()
        force_daily_send = os.getenv("FORCE_DAILY_SEND", "").strip().lower() in {"1", "true", "yes"}
        if store.has_recommendation_for_date(today) and not force_daily_send:
            print(f"Daily recommendation already exists for {today}; skipping duplicate send.")
            return 0

        zotero = ZoteroClient()
        zotero_items = zotero.existing_items() if zotero.configured else []
        candidates = search_all(config)
        candidates = filter_duplicates(candidates, store.seen_keys(), zotero_items)
        ranked = score_items(candidates)
        if not ranked:
            body = "# ASD 文献每日推荐 - " + today + "\n\n今天没有检索到候选文献，因此不生成推荐，也不写入推荐历史。"
            path = write_report(body, path_from_config(config, "daily_reports"), f"{today}.md")
            print(f"No literature candidates found. Empty report written: {path}")
            if can_send_email():
                send_email(f"[ASD文献推荐] {today}｜今日没有候选文献", body)
                print("No-candidate daily email sent.")
            else:
                print("Email not sent: MAIL_FROM and GMAIL_APP_PASSWORD are not fully configured.")
            return 0

        item, tier = select_daily_item(ranked)

        item.candidate_id = f"{today}_{short_hash(item.doi or item.title)}"
        store.save_candidate(item)
        store.save_recommendation(item)

        body = render_daily_report(item, low_confidence=(tier != "core"), alternatives=ranked[1:4])
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
