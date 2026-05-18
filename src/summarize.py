from __future__ import annotations

from datetime import date
from pathlib import Path

from .models import LiteratureItem


def render_daily_report(item: LiteratureItem, report_date: date | None = None) -> str:
    today = report_date or date.today()
    authors = ", ".join(item.authors[:8]) if item.authors else "作者信息待补充"
    abstract = item.abstract.strip() or "摘要暂未从检索源获取，建议打开原文页面后人工复核。"
    import_command = f"python scripts/approve_import.py --candidate-id {item.candidate_id} --add-to-zotero"
    return f"""# ASD 文献每日推荐 - {today.isoformat()}

## 今日推荐文献基本信息

- 题名：{item.title}
- 作者：{authors}
- 年份：{item.year or "待补充"}
- 期刊或平台：{item.venue or item.source or "待补充"}
- DOI：{item.doi or "待补充"}
- URL：{item.url or "待补充"}
- candidate_id：{item.candidate_id}

## 为什么推荐这篇

这篇文献与当前课题关键词的匹配度为 {item.score}，主要命中：{item.reason}。

## 文章讲了什么

{abstract}

## 我能从中学到什么

可以重点看它如何定义社会线索、动作目标或心智化变量，以及是否使用动态刺激、EEG、眼动或低水平视觉控制。这些信息能帮助你判断材料设计和实验解释是否足够贴近“动态社会意图加工”。

## 和我的课题哪一部分相关

{item.module}

## 这篇文章有什么局限

自动日报只能基于题名、摘要和开放元数据初筛。是否真正适合纳入阅读清单，需要进一步查看全文的方法、样本年龄、ASD 诊断标准、刺激材料和统计设计。

## 是否建议导入 Zotero

建议先人工打开 URL/DOI 复核。若确认适合导入，请运行：

```bash
{import_command}
```
"""


def render_weekly_report(items: list[LiteratureItem], report_date: date | None = None) -> str:
    today = report_date or date.today()
    top = sorted(items, key=lambda row: row.score, reverse=True)[:3]
    all_rows = "\n".join(
        f"- {idx}. {item.title} ({item.year or '年份待补充'}) - {item.module} - score {item.score}"
        for idx, item in enumerate(items, 1)
    ) or "- 本周暂无推荐记录。"
    top_rows = "\n\n".join(
        f"### Top {idx}: {item.title}\n\n- candidate_id：{item.candidate_id}\n- 推荐理由：{item.reason}\n- 课题启发：优先检查它对 {item.module} 的操作化定义和实验材料。"
        for idx, item in enumerate(top, 1)
    ) or "本周暂无足够候选。"
    focus = _next_focus(top)
    return f"""# ASD 文献周总结 - {today.isoformat()}

## 本周推荐过的全部文献列表

{all_rows}

## 本周最值得读的 3 篇

{top_rows}

## 对课题的启发

本周推荐应优先服务于“动态社会意图加工”的材料、任务和指标设计。阅读时建议记录每篇文章的刺激类型、被试年龄、ASD 诊断信息、主要行为/EEG/眼动指标，以及作者如何控制低水平视觉因素。

## 下周建议重点关注

{focus}
"""


def write_report(body: str, directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(body, encoding="utf-8-sig")
    return path


def daily_subject(item: LiteratureItem, report_date: date | None = None) -> str:
    today = report_date or date.today()
    return f"[ASD文献推荐] {today.isoformat()}｜今日推荐：{item.title[:80]}"


def weekly_subject(report_date: date | None = None) -> str:
    today = report_date or date.today()
    return f"[ASD文献周总结] {today.isoformat()}｜本周Top 3文献"


def _next_focus(items: list[LiteratureItem]) -> str:
    modules = [item.module for item in items]
    if modules.count("A") >= 2:
        return "模块 B：目标导向动作理解。A 类线索检测已有输入后，下周可补动作目标和预测机制。"
    if modules.count("B") >= 2:
        return "模块 C：隐含意图 / 心智化。B 类动作理解之后需要接上更高阶社会推断。"
    return "方法学：动态视频刺激、EEG/眼动同步指标和低水平视觉控制。"
