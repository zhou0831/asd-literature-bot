from __future__ import annotations

from datetime import date
from pathlib import Path
import re

from .llm import generate_article_overview_with_mimo
from .models import LiteratureItem


def render_daily_report(item: LiteratureItem, report_date: date | None = None) -> str:
    today = report_date or date.today()
    authors = ", ".join(item.authors[:8]) if item.authors else "作者信息待补充"
    chinese_overview = summarize_article_in_chinese(item)
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

{chinese_overview}

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


def summarize_article_in_chinese(item: LiteratureItem) -> str:
    try:
        mimo_overview = generate_article_overview_with_mimo(item)
    except Exception as exc:
        print(f"Warning: Mimo overview generation failed, using rule-based fallback: {exc}")
        mimo_overview = None
    if mimo_overview:
        return mimo_overview

    text = _clean_text(f"{item.title}. {item.abstract}")
    if not item.abstract.strip():
        return (
            f"这篇文献题名显示，它主要关注“{item.title}”。检索源没有返回可用摘要，"
            "所以目前只能把它作为候选文献处理；建议打开 DOI/URL 后复核研究对象、任务材料、主要指标和结论。"
        )

    topic = _topic_sentence(text)
    design = _design_sentence(text)
    result = _result_sentence(text)
    relevance = _relevance_sentence(item, text)
    return "\n\n".join([topic, design, result, relevance])


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


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _topic_sentence(text: str) -> str:
    lowered = text.lower()
    parts = ["这篇文章主要讨论 ASD/自闭症相关问题"]
    if "joint attention" in lowered:
        parts.append("共同注意")
    if "gaze" in lowered or "eye tracking" in lowered or "eye-tracking" in lowered:
        parts.append("凝视线索或眼动/视觉注意")
    if "theory of mind" in lowered or "mentalizing" in lowered:
        parts.append("心理理论或心智化")
    if "social cognition" in lowered or "social intention" in lowered:
        parts.append("社会认知或社会意图加工")
    if "action" in lowered or "goal" in lowered or "prediction" in lowered:
        parts.append("动作理解、目标推断或预测")
    if len(parts) == 1:
        parts.append("社会沟通、认知或方法学评估")
    return "；".join(parts) + "。"


def _design_sentence(text: str) -> str:
    lowered = text.lower()
    details: list[str] = []
    sample = re.search(r"\bn\s*=\s*(\d+)", lowered)
    if sample:
        details.append(f"摘要中提到样本量约为 n={sample.group(1)}")
    age = re.search(r"(\d+)\s*(?:-|to|–)\s*(\d+)\s*years?", lowered)
    if age:
        details.append(f"被试年龄范围约为 {age.group(1)}-{age.group(2)} 岁")
    if "children" in lowered or "child" in lowered:
        details.append("研究对象包含儿童或儿童发展样本")
    if "eeg" in lowered or "erp" in lowered:
        details.append("方法上涉及 EEG/ERP 指标")
    if "eye tracking" in lowered or "eye-tracking" in lowered:
        details.append("方法上涉及眼动或视觉注意测量")
    if "review" in lowered or "scoping review" in lowered or "meta-analysis" in lowered:
        details.append("文章类型偏综述或范围综述")
    if not details:
        details.append("摘要提示它围绕研究问题、方法和结果进行了常规实证或综述性分析")
    return "从研究设计看，" + "；".join(details) + "。"


def _result_sentence(text: str) -> str:
    lowered = text.lower()
    if "conclusion" in lowered or "results" in lowered or "findings" in lowered:
        return (
            "从结果/结论看，作者试图说明相关社会认知或方法学指标如何区分 ASD 与典型发展样本，"
            "或如何解释 ASD 个体在社会线索加工、动作理解、注意分配上的差异。"
        )
    return "从摘要可见，这篇文章更适合作为初筛候选；具体效应大小、统计证据和结论强度仍需看全文确认。"


def _relevance_sentence(item: LiteratureItem, text: str) -> str:
    module_map = {
        "A": "模块 A：线索 / 代理检测",
        "B": "模块 B：目标导向动作理解",
        "C": "模块 C：隐含意图 / 心智化",
        "方法学": "方法学：EEG、眼动、动态刺激或低水平视觉控制",
        "综述": "综述：理论框架和研究脉络整理",
    }
    module = module_map.get(item.module, item.module)
    return f"对你的课题来说，它最值得先放在“{module}”下复核，重点看任务材料是否足够动态、社会性是否明确，以及是否控制了低水平视觉因素。"


def _next_focus(items: list[LiteratureItem]) -> str:
    modules = [item.module for item in items]
    if modules.count("A") >= 2:
        return "模块 B：目标导向动作理解。A 类线索检测已有输入后，下周可补动作目标和预测机制。"
    if modules.count("B") >= 2:
        return "模块 C：隐含意图 / 心智化。B 类动作理解之后需要接上更高阶社会推断。"
    return "方法学：动态视频刺激、EEG/眼动同步指标和低水平视觉控制。"
