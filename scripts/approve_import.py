from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config, path_from_config
from src.storage import Store
from src.zotero_client import ZoteroClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--add-to-zotero", action="store_true")
    args = parser.parse_args()

    config = load_config()
    store = Store(path_from_config(config, "database"))
    try:
        item = store.get_candidate(args.candidate_id)
        if not item:
            print(f"Candidate not found: {args.candidate_id}")
            return 2

        print(f"candidate_id: {item.candidate_id}")
        print(f"title: {item.title}")
        print(f"doi: {item.doi or 'N/A'}")
        print(f"url: {item.url or 'N/A'}")

        if not args.add_to_zotero:
            print("Dry review only. Add --add-to-zotero to import after manual confirmation.")
            return 0

        tag = config.get("research_profile", {}).get("import_tag", "GPT推荐")
        result = ZoteroClient().import_item(item, tag=tag)
        print("Imported to Zotero.")
        print(result)
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())

