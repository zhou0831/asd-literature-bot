from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

from .llm import generate_article_overview_with_mimo, generate_weekly_report_with_mimo
from .models import LiteratureItem


@dataclass(frozen=True)
class SummaryResult:
    text: str
    ai_generated: bool
    learning_points: list[str] | None = None
    relevance: str = ""
    limitations: str = ""
    ai_failed: bool = False


def render_daily_report(item: LiteratureItem, report_date: date | None = None, low_confidence: bool = False) -> str:
    today = report_date or date.today()
    authors = ", ".join(item.authors[:8]) if item.authors else "作者信息待补充"
    overview = summarize_article_in_chinese(item)
    ai_note = _ai_generation_note(overview.ai_generated, overview.ai_failed)
    learning_points = _learning_points_text(item, overview)
    relevance = overview.relevance or _relevance_sentence(item, f"{item.title}. {item.abstract}")
    limitations = overview.limitations or _limitations_text(item)
    import_command = f"python scripts/approve_import.py --candidate-id {item.candidate_id} --add-to-zotero"
    zotero_block = _zotero_block(import_command, low_confidence or item.low_confidence or item.strong_exclusion)
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

这篇文献的 topic_fit_score 为 {item.topic_fit_score}，recommendation_score 为 {item.recommendation_score}。主要命中：{item.reason}。

## 文章讲了什么

{overview.text}

## 我能从中学到什么

{learning_points}

## 和我的课题哪一部分相关

{relevance}

## 这篇文章有什么局限

{limitations}

## 是否建议导入 Zotero

{zotero_block}

{ai_note}
"""


def render_no_high_match_report(candidates: list[LiteratureItem], report_date: date | None = None) -> str:
    today = report_date or date.today()
    rows = "\n\n".join(_low_match_candidate_text(item, idx) for idx, item in enumerate(candidates[:3], 1))
    return f"""# ASD 文献每日推荐 - {today.isoformat()}

## 今日结果

今天没有找到达到核心精读标准的高匹配文献，因此不生成正式推荐，也不建议导入 Zotero。

最低标准：topic_fit_score >= 50，recommendation_score >= 55，且没有 strong_exclusion。

## 低匹配备选

{rows or "今天没有可列出的候选文献。"}
"""


def summarize_article_in_chinese(item: LiteratureItem) -> SummaryResult:
    ai_failed = False
    try:
        mimo_summary = generate_article_overview_with_mimo(item)
    except Exception as exc:
        print(f"Warning: Mimo overview generation failed, using rule-based fallback: {exc}")
        mimo_summary = None
        ai_failed = True
    if mimo_summary:
        return SummaryResult(
            mimo_summary["overview"],
            ai_generated=True,
            learning_points=mimo_summary.get("learning_points") or [],
            relevance=mimo_summary.get("relevance") or "",
            limitations=mimo_summary.get("limitations") or "",
        )
    if ai_failed:
        print("Warning: AI summary validation failed; using rule-based fallback.")

    text = _clean_text(f"{item.title}. {item.abstract}")
    if not item.abstract.strip():
        return SummaryResult(
            f"这篇文献题名显示，它主要关注“{item.title}”。检索源没有返回可用摘要，"
            "所以目前只能把它作为候选文献处理；建议打开 DOI/URL 后复核研究对象、任务材料、主要指标和结论。",
            ai_generated=False,
            ai_failed=ai_failed,
        )

    topic = _topic_sentence(text)
    design = _design_sentence(text)
    result = _result_sentence(text)
    relevance = _relevance_sentence(item, text)
    return SummaryResult("\n\n".join([topic, design, result, relevance]), ai_generated=False, ai_failed=ai_failed)


def render_weekly_report(items: list[LiteratureItem], report_date: date | None = None) -> str:
    today = report_date or date.today()
    ranked = sorted(items, key=lambda row: row.score, reverse=True)
    top = ranked[:3]
    all_rows = "\n".join(
        f"- {idx}. {item.title} ({item.year or '年份待补充'}) - {item.module} - score {item.score}"
        for idx, item in enumerate(ranked, 1)
    ) or "- 本周暂无推荐记录。"
    weekly_insight = summarize_weekly_in_chinese(top)
    focus = _next_focus(top)
    top_heading = f"本周最值得读的 {len(top)} 篇" if top else "本周最值得读的文献"
    return f"""# ASD 文献周总结 - {today.isoformat()}

## 本周推荐过的全部文献列表

{all_rows}

## {top_heading}

{weekly_insight.text}

## 对课题的启发

本周推荐应优先服务于“动态社会意图加工”的材料、任务和指标设计。阅读时建议记录每篇文章的刺激类型、被试年龄、ASD 诊断信息、主要行为/EEG/眼动指标，以及作者如何控制低水平视觉因素。

## 下周建议重点关注

{focus}

{_ai_generation_note(weekly_insight.ai_generated)}
"""


def summarize_weekly_in_chinese(items: list[LiteratureItem]) -> SummaryResult:
    try:
        mimo_summary = generate_weekly_report_with_mimo(items)
    except Exception as exc:
        print(f"Warning: Mimo weekly summary failed, using rule-based fallback: {exc}")
        mimo_summary = None
    if mimo_summary:
        return SummaryResult(mimo_summary, ai_generated=True)

    top_rows = "\n\n".join(
        f"### Top {idx}: {item.title}\n\n- candidate_id：{item.candidate_id}\n- 推荐理由：{item.reason}\n- 课题启发：优先检查它对 {item.module} 的操作化定义和实验材料。"
        for idx, item in enumerate(items, 1)
    ) or "本周暂无足够候选。"
    return SummaryResult(top_rows, ai_generated=False)


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


def _ai_generation_note(ai_generated: bool, ai_failed: bool = False) -> str:
    if ai_failed:
        return "## AI 生成提醒\n\nAI 摘要校验失败，本段采用规则化摘要；邮件未包含模型原始输出。"
    if not ai_generated:
        return ""
    return (
        "## AI 生成提醒\n\n"
        "本邮件中的部分解读内容由 MiMo 大模型根据题名、摘要和开放元数据生成，"
        "可能存在遗漏或理解偏差。正式阅读、引用或导入 Zotero 前，请以原文和 DOI 页面为准。"
    )


def _learning_points_text(item: LiteratureItem, overview: SummaryResult) -> str:
    if overview.learning_points:
        return "\n".join(f"- {point}" for point in overview.learning_points[:4])
    points: list[str] = []
    if item.module == "A":
        points.append("看它是否把 gaze cueing、joint attention 或代理线索拆成可操作的动态指标。")
    elif item.module == "B":
        points.append("看它如何定义动作目标、动作预测和意图线索，是否能映射到目标导向动作理解。")
    elif item.module == "C":
        points.append("看它是否涉及 social attribution、false belief、ToM 或 mentalizing，可否支持隐含意图加工假设。")
    elif item.module == "方法学":
        points.append("看它的方法是否能服务于动态视频、EEG/眼动同步或时间序列指标，而不只是静态分类。")
    else:
        points.append("看它是否提供可迁移的理论框架，而不是泛泛背景综述。")
    if item.penalty_reasons:
        points.append("注意降权原因：" + "，".join(item.penalty_reasons) + "；这些点决定它是否只适合作背景阅读。")
    points.append(f"复核 topic_fit_score={item.topic_fit_score} 是否符合你当前课题的核心问题。")
    return "\n".join(f"- {point}" for point in points)


def _limitations_text(item: LiteratureItem) -> str:
    if item.strong_exclusion or item.low_confidence:
        return (
            "这篇文章只与眼动/视觉注意或 ASD 诊断背景相关，不直接涉及动态社会意图加工、"
            "A/B/C 模块、H_intent/H_belief、EEG/眼动对齐。因此不建议作为今日核心精读文献。"
        )
    return "自动日报只能基于题名、摘要和开放元数据初筛；正式阅读前仍需核对样本、任务材料、统计设计和全文结论。"


def _zotero_block(import_command: str, low_confidence: bool) -> str:
    if low_confidence:
        return "不建议导入 Zotero。若你人工复核后仍想保留，可再手动运行导入命令。"
    return "建议先人工打开 URL/DOI 复核。若确认适合导入，请运行：\n\n```bash\n" + import_command + "\n```"


def _low_match_candidate_text(item: LiteratureItem, idx: int) -> str:
    if item.strong_exclusion or item.penalty_reasons:
        judgment = (
            "这篇文章只与眼动/视觉注意、ASD 诊断背景或非核心分类任务相关，不直接涉及动态社会意图加工、"
            "A/B/C 模块、H_intent/H_belief、EEG/眼动对齐。因此不建议作为今日核心精读文献，也不建议导入 Zotero。"
        )
    else:
        judgment = (
            "这篇文章有一定相关性，但按当前评分还没有达到今日核心精读标准。建议先作为备选背景阅读，"
            "暂不导入 Zotero；如果你人工复核后认为它直接服务于动态社会意图加工，再单独处理。"
        )
    return (
        f"### 备选 {idx}: {item.title}\n\n"
        f"- topic_fit_score：{item.topic_fit_score}\n"
        f"- recommendation_score：{item.recommendation_score}\n"
        f"- 模块：{item.module}\n"
        f"- 降权原因：{', '.join(item.penalty_reasons) or '无'}\n"
        f"- 判断：{judgment}"
    )


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
