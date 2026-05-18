from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config, path_from_config
from src.storage import Store


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--format", choices=["md", "csv"], default="md")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    config = load_config()
    store = Store(path_from_config(config, "database"))
    try:
        items = store.recent_recommendations(limit=args.limit)
    finally:
        store.close()

    output = Path(args.output) if args.output else ROOT / "reports" / f"recommendations.{args.format}"
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "csv":
        with output.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["candidate_id", "title", "year", "venue", "doi", "url", "score", "module"])
            for item in items:
                writer.writerow([item.candidate_id, item.title, item.year, item.venue, item.doi, item.url, item.score, item.module])
    else:
        lines = ["# ASD 文献推荐历史", ""]
        for idx, item in enumerate(items, 1):
            lines.extend(
                [
                    f"## {idx}. {item.title}",
                    "",
                    f"- candidate_id：{item.candidate_id}",
                    f"- 年份：{item.year or '待补充'}",
                    f"- 期刊或平台：{item.venue or item.source or '待补充'}",
                    f"- DOI：{item.doi or '待补充'}",
                    f"- URL：{item.url or '待补充'}",
                    f"- 评分：{item.score}",
                    f"- 模块：{item.module}",
                    "",
                    "导入 Zotero 可在 GitHub Actions 里运行 `Approve Zotero Import`，输入上面的 candidate_id。",
                    "",
                ]
            )
        output.write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"Wrote {len(items)} recommendations to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
