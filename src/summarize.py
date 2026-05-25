from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from collections import Counter
import re

from .diagnostics import SearchDiagnostics, build_search_diagnostics
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


def render_daily_report(
    item: LiteratureItem,
    report_date: date | None = None,
    low_confidence: bool = False,
    alternatives: list[LiteratureItem] | None = None,
    candidate_diagnostics: SearchDiagnostics | dict | None = None,
) -> str:
    today = report_date or date.today()
    authors = ", ".join(item.authors[:8]) if item.authors else "作者信息待补充"
    overview = summarize_article_in_chinese(item)
    ai_note = _ai_generation_note(overview.ai_generated, overview.ai_failed)
    learning_points = _learning_points_text(item, overview)
    relevance = overview.relevance or _relevance_sentence(item, f"{item.title}. {item.abstract}")
    limitations = overview.limitations or _limitations_text(item)
    import_command = f"python scripts/approve_import.py --candidate-id {item.candidate_id} --add-to-zotero"
    tier = item.recommendation_tier or ("core" if not low_confidence else "exploratory")
    zotero_block = _zotero_block(import_command, tier)
    alternatives_block = _alternatives_block(alternatives or [], item)
    diagnostics_block = render_candidate_diagnostics(candidate_diagnostics) if candidate_diagnostics else ""
    return f"""# ASD 文献每日推荐 - {today.isoformat()}

## 今日推荐类型

{_tier_label(tier)}

## 今日推荐文献基本信息

- 题名：{item.title}
- 作者：{authors}
- 年份：{item.year or "待补充"}
- 期刊或平台：{item.venue or item.source or "待补充"}
- DOI：{item.doi or "待补充"}
- URL：{item.url or "待补充"}
- candidate_id：{item.candidate_id}

## 元数据状态

- 摘要状态：{item.abstract_status or _abstract_status(item)}
- 摘要来源：{item.abstract_source or "待补充"}
- 检索来源：{item.source or "待补充"}
- 元数据来源：{", ".join(item.metadata_sources) or "待补充"}
- 判断可靠性：{_metadata_reliability(item)}

## 为什么今天推荐它

{_tier_reason(tier)}

## 分数

- topic_fit_score：{item.topic_fit_score}
- recommendation_score：{item.recommendation_score}
- recommendation_tier：{tier}
- reading_priority：{item.reading_priority}
- module：{item.module}
- penalty_reasons：{', '.join(item.penalty_reasons) or '无'}
- strong_exclusion：{item.strong_exclusion}

## 阅读优先级

{item.reading_priority or "defer"}

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

{alternatives_block}

{diagnostics_block}

{ai_note}
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


def build_candidate_diagnostics(
    raw_candidates: list[LiteratureItem],
    deduped_candidates: list[LiteratureItem],
    ranked_candidates: list[LiteratureItem],
    selected: LiteratureItem | None = None,
) -> SearchDiagnostics:
    return build_search_diagnostics(raw_candidates, deduped_candidates, ranked_candidates, selected)


def render_candidate_diagnostics(diagnostics: SearchDiagnostics | dict) -> str:
    if isinstance(diagnostics, dict):
        diagnostics = SearchDiagnostics(**diagnostics)
    source_counts = diagnostics.source_counts or Counter()
    module_counts = diagnostics.module_counts or Counter()
    tier_counts = diagnostics.tier_counts or Counter()
    strong_exclusions = diagnostics.excluded_preview or []
    high_unselected = diagnostics.high_score_not_selected_preview or []
    module_order = ["A", "B", "C1", "C2", "方法学", "综述"]
    tier_order = ["core", "exploratory", "background"]

    lines = [
        "## 检索诊断",
        "",
        f"- 原始候选数：{diagnostics.raw_candidate_count}",
        f"- 去重后候选数：{diagnostics.deduped_candidate_count}",
        f"- 有摘要候选数：{diagnostics.abstract_full_count}",
        f"- 无摘要候选数：{diagnostics.abstract_missing_count}",
        "- 各来源候选数："
        + "；".join(f"{source} {source_counts.get(source, 0)}" for source in ["PubMed", "Europe PMC", "OpenAlex"]),
        "- 各模块候选数："
        + "；".join(f"{module} {module_counts.get(module, 0)}" for module in module_order),
        "- 推荐层级候选数："
        + "；".join(f"{tier} {tier_counts.get(tier, 0)}" for tier in tier_order)
        + f"；strong_exclusion {diagnostics.strong_exclusion_count}",
        "",
        "### 被 strong_exclusion 排除的前 5 篇",
    ]
    if strong_exclusions:
        lines.extend(_compact_candidate_line(item) for item in strong_exclusions)
    else:
        lines.append("- 无")
    lines.extend(["", "### 未被选中的高分候选前 5 篇"])
    if high_unselected:
        lines.extend(_compact_candidate_line(item) for item in high_unselected)
    else:
        lines.append("- 无")
    return "\n".join(lines)


def render_weekly_report(items: list[LiteratureItem], report_date: date | None = None) -> str:
    today = report_date or date.today()
    ranked = sorted(items, key=_weekly_rank_key, reverse=True)
    top = select_weekly_top3(items)
    all_rows = "\n".join(
        f"- {idx}. {item.title} ({item.year or '年份待补充'}) - {_tier_label(item.recommendation_tier)} - {item.reading_priority} - {item.module} - score {item.recommendation_score}"
        for idx, item in enumerate(ranked, 1)
    ) or "- 本周暂无推荐记录。"
    weekly_insight = summarize_weekly_in_chinese(top)
    focus = _next_focus(top)
    discard = _weekly_discard_text(ranked, top)
    top_heading = f"本周最值得读的 {len(top)} 篇" if top else "本周最值得读的文献"
    return f"""# ASD 文献周总结 - {today.isoformat()}

## 本周推荐过的全部文献列表

{all_rows}

## {top_heading}

{weekly_insight.text}

## 对课题的启发

本周推荐应优先服务于“动态社会意图加工”的材料、任务和指标设计。阅读时建议记录每篇文章的刺激类型、被试年龄、ASD 诊断信息、主要行为/EEG/眼动指标，以及作者如何控制低水平视觉因素。

## 可以略读或放弃的每日推荐

{discard}

## 下周建议重点关注

{focus}

{_ai_generation_note(weekly_insight.ai_generated)}
"""


def select_weekly_top3(items: list[LiteratureItem], limit: int = 3) -> list[LiteratureItem]:
    eligible = [
        item
        for item in items
        if item.reading_priority != "exclude"
        and not item.strong_exclusion
        and not _weekly_excluded(item)
    ]
    if not eligible:
        eligible = [item for item in items if item.reading_priority != "exclude" and not item.strong_exclusion]
    if not eligible:
        eligible = list(items)
    return sorted(eligible, key=_weekly_rank_key, reverse=True)[:limit]


def select_weekly_top(items: list[LiteratureItem], limit: int = 3) -> list[LiteratureItem]:
    return select_weekly_top3(items, limit)


def summarize_weekly_in_chinese(items: list[LiteratureItem]) -> SummaryResult:
    try:
        mimo_summary = generate_weekly_report_with_mimo(items)
    except Exception as exc:
        print(f"Warning: Mimo weekly summary failed, using rule-based fallback: {exc}")
        mimo_summary = None
    if mimo_summary:
        return SummaryResult(mimo_summary, ai_generated=True)

    top_rows = "\n\n".join(
        f"### Top {idx}: {item.title}\n\n- candidate_id：{item.candidate_id}\n- 推荐类型：{_tier_label(item.recommendation_tier)}\n- reading_priority：{item.reading_priority}\n- 入选原因：{_weekly_selection_reason(item)}\n- 推荐理由：{item.reason}\n- 课题启发：优先检查它对 {item.module} 的操作化定义和实验材料。{_low_tier_weekly_note(item)}"
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
    elif item.module in {"C1", "C2"}:
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
        return _module_specific_low_confidence_note(item)
    return "自动日报只能基于题名、摘要和开放元数据初筛；正式阅读前仍需核对样本、任务材料、统计设计和全文结论。"


def _abstract_status(item: LiteratureItem) -> str:
    if len((item.abstract or "").strip()) >= 80:
        return "full"
    if item.abstract.strip():
        return "metadata_only"
    if item.title and any([item.year, item.venue, item.doi, item.url, item.authors]):
        return "metadata_only"
    if item.title:
        return "title_only"
    return "missing"


def _metadata_reliability(item: LiteratureItem) -> str:
    if item.abstract_status == "full" or len((item.abstract or "").strip()) >= 80:
        return "中等：有可用摘要，但仍需打开全文复核任务和结果。"
    if item.doi or item.pmid or item.pmcid:
        return "偏低：有基础元数据，但摘要不足，建议只作初筛。"
    return "低：元数据不足，不建议直接导入 Zotero。"


def _module_specific_low_confidence_note(item: LiteratureItem) -> str:
    if item.reading_priority == "exclude" or item.strong_exclusion:
        return "这篇文章明显偏离当前课题核心，不建议精读，也不建议导入 Zotero。"
    if item.module == "A":
        return "这篇文章主要贴近 A 模块，即社会线索、共同注意或 gaze cue 的接入问题。它不一定涉及 C1/C2 或 H_intent/H_belief，但可作为社会入口任务或眼动指标参考。"
    if item.module == "B":
        return "这篇文章主要贴近 B 模块，即动作目标预测或 anticipatory gaze。它不一定涉及高阶心智化，但可为 H_goal 或 prediction readout 提供参考。"
    if item.module == "C1":
        return "这篇文章主要贴近 C1，即 social attribution / moving shapes / 隐含互动意图。重点复核它是否有低语言作答方式、动态刺激和可对齐的关键时间窗口。"
    if item.module == "C2":
        return "这篇文章主要贴近 C2，即 false belief / knowledge difference。重点复核它是否包含 belief-consistent looking、choose-the-ending 或低语言儿童友好 probe。"
    if item.module == "方法学":
        return "这篇文章主要是方法学参考，需要判断能否迁移到 EEG/眼动与 H(t) 对齐分析。"
    return "这篇文章更像背景材料，需要先判断它是否真正服务当前任务设计、刺激材料或时序指标。"


def _zotero_block(import_command: str, tier: str) -> str:
    if tier != "core":
        return "不建议直接导入 Zotero，除非人工复核后确认确实有用。若确认要保留，可手动运行导入命令。"
    return "建议先人工打开 URL/DOI 复核。若确认适合导入，请运行：\n\n```bash\n" + import_command + "\n```"


def _tier_label(tier: str) -> str:
    return {
        "core": "核心推荐",
        "exploratory": "低置信推荐",
        "background": "背景候选",
        "very_low_confidence": "极低置信候选",
    }.get(tier or "core", tier or "核心推荐")


def _tier_reason(tier: str) -> str:
    if tier == "core":
        return "这篇文章达到当前课题核心精读标准，因此作为今日核心推荐。"
    if tier == "exploratory":
        return "今天没有检索到达到核心精读标准的文献，因此系统选择当天相关性最高且未被 strong_exclusion 排除的候选作为低置信推荐。它不一定适合直接导入 Zotero，但适合先快速浏览。"
    if tier == "background":
        return "这篇文章只与课题部分相关，主要作为背景补充。建议快速浏览，不建议直接导入 Zotero。"
    return "今天所有候选都较弱，系统仍按每日推荐规则选择最高分候选。建议仅作检索记录，不建议精读或导入 Zotero。"


def _alternatives_block(alternatives: list[LiteratureItem], selected: LiteratureItem) -> str:
    if not alternatives:
        return "## 其他备选候选\n\n今天没有更多备选候选。"
    rows = []
    for item in alternatives[:3]:
        rows.append(
            f"- 标题：{item.title}\n"
            f"  - topic_fit_score：{item.topic_fit_score}\n"
            f"  - recommendation_score：{item.recommendation_score}\n"
            f"  - module：{item.module}\n"
            f"  - penalty_reasons：{', '.join(item.penalty_reasons) or '无'}\n"
            f"  - 为什么没有选为今日推荐：{_not_selected_reason(item, selected)}"
        )
    return "## 其他备选候选\n\n" + "\n".join(rows)


def _not_selected_reason(item: LiteratureItem, selected: LiteratureItem) -> str:
    if item.strong_exclusion:
        return "存在 strong_exclusion，优先级低于主推荐。"
    if item.recommendation_score < selected.recommendation_score:
        return "recommendation_score 低于今日主推荐。"
    return "与今日主推荐相比，课题贴合度或可读价值略低。"


def _compact_candidate_line(item: LiteratureItem) -> str:
    penalties = ", ".join(item.penalty_reasons) or "无"
    return (
        f"- {item.title} | module={item.module} | topic_fit={item.topic_fit_score} | "
        f"score={item.recommendation_score} | tier={item.recommendation_tier} | "
        f"reading_priority={item.reading_priority} | penalties={penalties}"
    )


def _low_tier_weekly_note(item: LiteratureItem) -> str:
    if item.recommendation_tier in {"exploratory", "background", "very_low_confidence"}:
        return " 这篇是低置信推荐，进入 Top 3 是因为本周候选池整体较弱，仍需人工复核。"
    return ""


def _weekly_selection_reason(item: LiteratureItem) -> str:
    if item.reading_priority == "deep_read":
        return "达到 deep_read 优先级，且未被 strong_exclusion 排除，适合作为本周优先精读候选。"
    if item.reading_priority == "skim":
        return f"属于 skim 候选，但直接贴近 {item.module} 模块，可快速复核其任务、刺激或指标设计。"
    if item.reading_priority == "defer":
        return "本周候选池较弱，仅作背景补位；不建议直接导入 Zotero。"
    return "仅作为检索记录保留，不建议进入精读。"


def _weekly_discard_text(ranked: list[LiteratureItem], top: list[LiteratureItem]) -> str:
    top_ids = {item.candidate_id for item in top}
    rest = [item for item in ranked if item.candidate_id not in top_ids]
    if not rest:
        return "本周没有需要额外放弃的每日推荐。"
    rows = []
    for item in rest:
        rows.append(f"- {item.title}：{_tier_label(item.recommendation_tier)}，不建议导入 Zotero，除非人工复核后确认与课题直接相关。")
    return "\n".join(rows)


def _weekly_rank_key(item: LiteratureItem) -> tuple:
    priority_rank = {"deep_read": 4, "skim": 3, "defer": 1, "exclude": 0}
    tier_rank = {"core": 4, "exploratory": 2, "background": 1, "very_low_confidence": 0}
    direct_module = 2 if item.module in {"A", "B", "C1", "C2"} else 1 if item.module == "方法学" else 0
    has_metadata = 1 if item.abstract.strip() or (item.doi and item.url) else 0
    return (
        priority_rank.get(item.reading_priority, 1),
        tier_rank.get(item.recommendation_tier, 1),
        direct_module,
        has_metadata,
        item.recommendation_score,
        item.topic_fit_score,
    )


def _weekly_excluded(item: LiteratureItem) -> bool:
    excluded_penalties = {
        "generic_ai_diagnosis",
        "facial_recognition_only",
        "broad_visual_attention_diagnosis",
        "generic_classification",
        "intervention_only",
        "language_intervention_only",
        "adhd_error_monitoring_only",
        "generic_erp_biomarker",
        "response_commentary",
        "diagnostic_scoping_review",
    }
    if any(reason in excluded_penalties for reason in item.penalty_reasons):
        return True
    text = f"{item.title} {item.abstract}".lower()
    return any(
        re.search(pattern, text)
        for pattern in [
            r"home[- ]based intervention",
            r"speech therapy",
            r"language strateg",
            r"response to\b",
            r"\bcommentary\b",
            r"\badhd\b.*error monitoring",
        ]
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
        "C1": "模块 C1：社会归因 / moving shapes",
        "C2": "模块 C2：错误信念 / 心智化",
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
