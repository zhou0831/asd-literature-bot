from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_dotenv
from src.zotero_client import ZoteroClient


def main() -> int:
    load_dotenv()
    client = ZoteroClient()
    if not client.configured:
        print("Zotero is not configured. Set ZOTERO_API_KEY, ZOTERO_USER_ID, and ZOTERO_COLLECTION_KEY.")
        return 2
    items = client.existing_items()
    out = ROOT / "data" / "zotero_items.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(items)} Zotero item fingerprints to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

